package handlers

import (
	"encoding/json"
	"encoding/base64"
	"net/http"
	"strconv"
	"strings"
	"time"

	"backend-optimizer/internal/middleware"
	"backend-optimizer/internal/models"
)

// GET /user/details
func (h *Handler) UserDetails(w http.ResponseWriter, r *http.Request) {
	// Either their own ID or from query param
	userID := r.URL.Query().Get("user_id")
	if userID == "" {
		userID = middleware.UserIDFromCtx(r.Context())
	}

	var res models.UserDetailResponse
	err := h.DB.QueryRow(r.Context(), "SELECT user_id, username, display_name, post_count FROM users WHERE user_id = $1", userID).
		Scan(&res.UserID, &res.Username, &res.DisplayName, &res.PostCount)
	
	if err != nil {
		http.Error(w, `{"error": "user_not_found"}`, http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(res)
}

// POST /user/delete
func (h *Handler) UserDelete(w http.ResponseWriter, r *http.Request) {
	userID := middleware.UserIDFromCtx(r.Context())

	// CASCADE in Postgres handles removing related posts, likes, etc.
	res, err := h.DB.Exec(r.Context(), "DELETE FROM users WHERE user_id = $1", userID)
	if err != nil || res.RowsAffected() == 0 {
		http.Error(w, `{"error": "delete_failed"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(models.UserDeleteResponse{Success: true})
}

// GET /user/get_posts
func (h *Handler) UserGetPosts(w http.ResponseWriter, r *http.Request) {
	userID := r.URL.Query().Get("user_id")
	if userID == "" {
		userID = middleware.UserIDFromCtx(r.Context())
	}
	cursor := r.URL.Query().Get("cursor")

	limit := 20
	if lStr := r.URL.Query().Get("limit"); lStr != "" {
		if l, err := strconv.Atoi(lStr); err == nil && l > 0 && l <= 100 {
			limit = l
		}
	}

	authID := middleware.UserIDFromCtx(r.Context()) // for checking "liked_by_me"

	// Use explicit tuple ordering so Postgres natively leverages the (author_id, created_at) index
	query := `
		SELECT p.post_id, p.parent_post_id, p.author_id, p.content, p.created_at, p.like_count, p.comment_count,
		EXISTS(SELECT 1 FROM likes l WHERE l.post_id = p.post_id AND l.user_id = $1) as liked_by_me
		FROM posts p
		WHERE p.author_id = $2 `
	
	args := []interface{}{authID, userID}
	
	if cursor != "" {
		// Stateless base64 cursor decoding: "RFC3339Nano|post_id"
		decodedBytes, err := base64.URLEncoding.DecodeString(cursor)
		if err == nil {
			parts := strings.SplitN(string(decodedBytes), "|", 2)
			if len(parts) == 2 {
				query += ` AND (p.created_at, p.post_id) < ($3, $4)`
				args = append(args, parts[0], parts[1])
			}
		}
	}

	query += ` ORDER BY p.created_at DESC, p.post_id DESC LIMIT $` + strconv.Itoa(len(args)+1)
	args = append(args, limit)

	rows, err := h.DB.Query(r.Context(), query, args...)
	if err != nil {
		http.Error(w, `{"error": "db_error"}`, http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var posts []models.PostResponse
	var nextCursor *string

	for rows.Next() {
		var post models.PostResponse
		rows.Scan(&post.PostID, &post.ParentPostID, &post.AuthorID, &post.Content, &post.CreatedAt, &post.LikeCount, &post.CommentCount, &post.LikedByMe)
		posts = append(posts, post)
		
		lastID := post.PostID
		// Create stateless cursor preventing subquery dependencies
		cursorStr := base64.URLEncoding.EncodeToString([]byte(post.CreatedAt.Format(time.RFC3339Nano) + "|" + lastID))
		nextCursor = &cursorStr
	}

	if posts == nil {
		posts = []models.PostResponse{}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(models.PostListResponse{
		Posts:      posts,
		NextCursor: nextCursor,
	})
}

// GET /user/liked_posts
func (h *Handler) UserLikedPosts(w http.ResponseWriter, r *http.Request) {
	userID := r.URL.Query().Get("user_id")
	if userID == "" {
		userID = middleware.UserIDFromCtx(r.Context())
	}
	cursor := r.URL.Query().Get("cursor")
	
	limit := 20
	if lStr := r.URL.Query().Get("limit"); lStr != "" {
		if l, err := strconv.Atoi(lStr); err == nil && l > 0 && l <= 100 {
			limit = l
		}
	}

	authID := middleware.UserIDFromCtx(r.Context())

	// Sorting by likes.created_at, we can cursor using likes.created_at or a synthetic cursor.
	// Since likes don't have ULIDs, we use likes.created_at explicitly.
	query := `
		SELECT p.post_id, p.parent_post_id, p.author_id, p.content, p.created_at, p.like_count, p.comment_count,
		EXISTS(SELECT 1 FROM likes l2 WHERE l2.post_id = p.post_id AND l2.user_id = $1) as liked_by_me,
		l.created_at as liked_at
		FROM posts p
		JOIN likes l ON p.post_id = l.post_id
		WHERE l.user_id = $2 `
	
	args := []interface{}{authID, userID}
	
	if cursor != "" {
		decodedBytes, err := base64.URLEncoding.DecodeString(cursor)
		if err == nil {
			parts := strings.SplitN(string(decodedBytes), "|", 2)
			if len(parts) == 2 {
				query += ` AND (l.created_at, l.post_id) < ($3, $4)`
				args = append(args, parts[0], parts[1])
			}
		}
	}

	query += ` ORDER BY l.created_at DESC, l.post_id DESC LIMIT $` + strconv.Itoa(len(args)+1)
	args = append(args, limit)

	rows, err := h.DB.Query(r.Context(), query, args...)
	if err != nil {
		http.Error(w, `{"error": "db_error"}`, http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var posts []models.PostResponse
	var nextCursor *string

	for rows.Next() {
		var post models.PostResponse
		var likedAt time.Time
		rows.Scan(&post.PostID, &post.ParentPostID, &post.AuthorID, &post.Content, &post.CreatedAt, &post.LikeCount, &post.CommentCount, &post.LikedByMe, &likedAt)
		posts = append(posts, post)
		lastID := post.PostID
		cursorStr := base64.URLEncoding.EncodeToString([]byte(likedAt.Format(time.RFC3339Nano) + "|" + lastID))
		nextCursor = &cursorStr
	}

	if posts == nil {
		posts = []models.PostResponse{}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(models.PostListResponse{
		Posts:      posts,
		NextCursor: nextCursor,
	})
}
