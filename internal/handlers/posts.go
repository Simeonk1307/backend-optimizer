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
	"github.com/google/uuid"
)

// POST /posts/create
func (h *Handler) PostCreate(w http.ResponseWriter, r *http.Request) {
	userID := middleware.UserIDFromCtx(r.Context())

	// 1. Parse Multipart (Max 32MB)
	if err := r.ParseMultipartForm(32 << 20); err != nil {
		http.Error(w, `{"error": "invalid_form"}`, http.StatusBadRequest)
		return
	}

	content := r.FormValue("content")
	parentID := r.FormValue("parent_post_id")
	var parentPtr *string
	if parentID != "" {
		parentPtr = &parentID
	}

	// 2. Start Transaction for Atomic Updates
	tx, err := h.DB.Begin(r.Context())
	if err != nil {
		http.Error(w, `{"error": "db_error"}`, http.StatusInternalServerError)
		return
	}
	defer tx.Rollback(r.Context())

	// 3. Insert Post (Using your schema's p_ prefix default)
	var post models.PostResponse
	query := `
		INSERT INTO posts (author_id, content, parent_post_id)
		VALUES ($1, $2, $3)
		RETURNING post_id, author_id, content, parent_post_id, created_at, like_count, comment_count`
	
	err = tx.QueryRow(r.Context(), query, userID, content, parentPtr).
		Scan(&post.PostID, &post.AuthorID, &post.Content, &post.ParentPostID, &post.CreatedAt, &post.LikeCount, &post.CommentCount)
	if err != nil {
		return
	}

	// 4. Increment Parent Comment Count if applicable
	if parentPtr != nil {
		tx.Exec(r.Context(), "UPDATE posts SET comment_count = comment_count + 1 WHERE post_id = $1", *parentPtr)
	}

	// 5. Save Media
	files := r.MultipartForm.File["media[]"]
	for _, fHeader := range files {
		file, _ := fHeader.Open()
		
		// Generate filename
		mID := "m_" + uuid.New().String()
		ext := filepath.Ext(fHeader.Filename)
		fullName := mID + ext
		
		// Save to /app/media for Tester Validation
		dst, _ := os.Create(filepath.Join("./media", fullName))
		io.Copy(dst, file)
		file.Close()
		dst.Close()

		mType := "image"
		if strings.Contains(fHeader.Header.Get("Content-Type"), "video") {
			mType = "video"
		}

		tx.Exec(r.Context(), "INSERT INTO media (media_id, post_id, type, filename) VALUES ($1, $2, $3, $4)",
			mID, post.PostID, mType, fullName)

		post.Media = append(post.Media, models.MediaResponse{
			Type:    mType,
			MediaID: mID,
			URL:     "/media/" + fullName,
		})
	}

	tx.Commit(r.Context())
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(post)
}

// GET /posts/details?post_id=p_123
func (h *Handler) PostDetails(w http.ResponseWriter, r *http.Request) {
	postID := r.URL.Query().Get("post_id")
	userID := middleware.UserIDFromCtx(r.Context()) // Can be empty if public

	var post models.PostResponse
	// Optimized Join to get Post + Media in one go (or use two queries for simplicity)
	err := h.DB.QueryRow(r.Context(), `
		SELECT post_id, author_id, content, parent_post_id, created_at, like_count, comment_count,
		EXISTS(SELECT 1 FROM likes WHERE post_id = $1 AND user_id = $2) as liked_by_me
		FROM posts WHERE post_id = $1`, postID, userID).
		Scan(&post.PostID, &post.AuthorID, &post.Content, &post.ParentPostID, &post.CreatedAt, &post.LikeCount, &post.CommentCount, &post.LikedByMe)

	if err != nil {
		http.Error(w, `{"error": "not_found"}`, http.StatusNotFound)
		return
	}

	// Fetch Media
	rows, _ := h.DB.Query(r.Context(), "SELECT type, media_id, filename FROM media WHERE post_id = $1", postID)
	defer rows.Close()
	for rows.Next() {
		var m models.MediaResponse
		var fname string
		rows.Scan(&m.Type, &m.MediaID, &fname)
		m.URL = "/media/" + fname
		post.Media = append(post.Media, m)
	}

	json.NewEncoder(w).Encode(post)
}

// POST /posts/delete
func (h *Handler) PostDelete(w http.ResponseWriter, r *http.Request) {
	var req struct { PostID string `json:"post_id"` }
	json.NewDecoder(r.Body).Decode(&req)
	userID := middleware.UserIDFromCtx(r.Context())

	// Only delete if the user is the author
	res, err := h.DB.Exec(r.Context(), "DELETE FROM posts WHERE post_id = $1 AND author_id = $2", req.PostID, userID)
	
	if err != nil || res.RowsAffected() == 0 {
		http.Error(w, `{"error": "unauthorized_or_not_found"}`, http.StatusForbidden)
		return
	}

	json.NewEncoder(w).Encode(map[string]bool{"success": true})
}