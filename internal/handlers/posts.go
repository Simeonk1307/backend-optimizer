package handlers

import (
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"backend-optimizer/internal/middleware"
	"backend-optimizer/internal/models"
	"github.com/oklog/ulid/v2"
)

// POST /posts/create
func (h *Handler) PostCreate(w http.ResponseWriter, r *http.Request) {
	userID := middleware.UserIDFromCtx(r.Context())

	if err := r.ParseMultipartForm(32 << 20); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "invalid_form"})
		return
	}

	content := r.FormValue("content")
	parentPostID := r.FormValue("parent_post_id")
	
	var pIDVal interface{}
	if parentPostID != "" {
		pIDVal = parentPostID
	}

	tx, err := h.DB.Begin(r.Context())
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "db_error"})
		return
	}
	defer tx.Rollback(r.Context())

	postID := "p_" + ulid.Make().String()
	
	var pIDResp *string
	if parentPostID != "" {
		pIDResp = &parentPostID
	}

	post := models.PostCreateResponse{
		Media:        make([]models.MediaCreateResponse, 0),
		ParentPostID: pIDResp,
	}

	query := `
		INSERT INTO posts (post_id, parent_post_id, author_id, content)
		VALUES ($1, $2, $3, $4)
		RETURNING post_id, author_id, content, created_at`
	
	err = tx.QueryRow(r.Context(), query, postID, pIDVal, userID, content).
		Scan(&post.PostID, &post.AuthorID, &post.Content, &post.CreatedAt)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "create_failed"})
		return
	}

	// Triggers handle post_count and comment_count - don't update manually!

	// Ensure media directory exists
	os.MkdirAll("./media", 0755)

	files := r.MultipartForm.File["media[]"]
	for _, fHeader := range files {
		file, err := fHeader.Open()
		if err != nil {
			continue
		}
		
		mID := "m_" + ulid.Make().String()
		ext := filepath.Ext(fHeader.Filename)
		fullName := mID + ext
		
		dst, err := os.Create(filepath.Join("./media", fullName))
		if err != nil {
			file.Close()
			continue
		}

		io.Copy(dst, file)
		file.Close()
		dst.Close()

		mType := "image"
		if strings.Contains(fHeader.Header.Get("Content-Type"), "video") {
			mType = "video"
		}

		_, err = tx.Exec(r.Context(), 
			"INSERT INTO media (media_id, post_id, type, filename) VALUES ($1, $2, $3, $4)",
			mID, post.PostID, mType, fullName)
		
		if err != nil {
			continue
		}

		post.Media = append(post.Media, models.MediaCreateResponse{
			Type:    mType,
			MediaID: mID,
		})
	}

	if err = tx.Commit(r.Context()); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "commit_failed"})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(post)
}

// GET /posts/details
func (h *Handler) PostDetails(w http.ResponseWriter, r *http.Request) {
	buf := make([]byte, 1)
	n, _ := r.Body.Read(buf)
	if n > 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "body_must_be_null"})
		return
	}
	
	postID := r.URL.Query().Get("post_id")
	userID := middleware.UserIDFromCtx(r.Context())

	post := models.PostDetailResponse{
		Media: make([]models.MediaDetailResponse, 0),
	}

	err := h.DB.QueryRow(r.Context(), `
		SELECT post_id, parent_post_id, author_id, content, created_at, like_count, comment_count,
		EXISTS(SELECT 1 FROM likes WHERE post_id = $1 AND user_id = $2) as liked_by_me
		FROM posts WHERE post_id = $1`, postID, userID).
		Scan(&post.PostID, &post.ParentPostID, &post.AuthorID, &post.Content, 
			&post.CreatedAt, &post.LikeCount, &post.CommentCount, &post.LikedByMe)

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "not_found"})
		return
	}

	rows, err := h.DB.Query(r.Context(), 
		"SELECT type, media_id, filename FROM media WHERE post_id = $1", postID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "media_fetch_failed"})
		return
	}
	defer rows.Close()

	for rows.Next() {
		var m models.MediaDetailResponse
		var fname string
		if err := rows.Scan(&m.Type, &m.MediaID, &fname); err != nil {
			continue
		}
		m.URL = "/media/" + fname
		m.ThumbnailURL = "/media/" + fname
		post.Media = append(post.Media, m)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(post)
}

// POST /posts/delete
func (h *Handler) PostDelete(w http.ResponseWriter, r *http.Request) {
	var req struct { PostID string `json:"post_id"` }
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "invalid_json"})
		return
	}

	userID := middleware.UserIDFromCtx(r.Context())

	// Triggers handle post_count and comment_count - just delete!
	res, err := h.DB.Exec(r.Context(), 
		"DELETE FROM posts WHERE post_id = $1 AND author_id = $2", req.PostID, userID)
	
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "delete_failed"})
		return
	}

	if res.RowsAffected() == 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "not_found_or_unauthorized"})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]bool{"success": true})
}

// POST /posts/like
func (h *Handler) PostLike(w http.ResponseWriter, r *http.Request) {
	var req models.PostLikeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "invalid_json"})
		return
	}

	userID := middleware.UserIDFromCtx(r.Context())

	tx, err := h.DB.Begin(r.Context())
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "db_error"})
		return
	}
	defer tx.Rollback(r.Context())

	// Triggers handle like_count - just insert/delete!
	if req.Liked {
		_, err = tx.Exec(r.Context(), 
			"INSERT INTO likes (user_id, post_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", 
			userID, req.PostID)
	} else {
		_, err = tx.Exec(r.Context(), 
			"DELETE FROM likes WHERE user_id = $1 AND post_id = $2", 
			userID, req.PostID)
	}

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "like_operation_failed"})
		return
	}

	var likeCount int
	err = tx.QueryRow(r.Context(), 
		"SELECT like_count FROM posts WHERE post_id = $1", req.PostID).Scan(&likeCount)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "post_not_found"})
		return
	}

	if err = tx.Commit(r.Context()); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "commit_failed"})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(models.PostLikeResponse{
		PostID:    req.PostID,
		LikeCount: likeCount,
		LikedByMe: req.Liked,
	})
}