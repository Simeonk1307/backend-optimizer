package handlers

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
	"time"

	"backend-optimizer/internal/middleware"
	"backend-optimizer/internal/models"
)

// GET /user/get_posts
func (h *Handler) UserGetPosts(w http.ResponseWriter, r *http.Request) {
	buf := make([]byte, 1)
	n, _ := r.Body.Read(buf)
	if n > 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "body_must_be_null"})
		return
	}

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

	query := `
		SELECT p.post_id, p.parent_post_id, p.author_id, p.content, p.created_at, p.like_count, p.comment_count,
		EXISTS(SELECT 1 FROM likes l WHERE l.post_id = p.post_id AND l.user_id = $1) as liked_by_me
		FROM posts p
		WHERE p.author_id = $2`
	
	args := []interface{}{authID, userID}
	
	if cursor != "" {
		decodedBytes, err := base64.URLEncoding.DecodeString(cursor)
		if err == nil {
			parts := strings.SplitN(string(decodedBytes), "|", 2)
			if len(parts) == 2 {
				createdAt, parseErr := time.Parse(time.RFC3339Nano, parts[0])
				if parseErr == nil {
					query += ` AND (p.created_at, p.post_id) < ($3, $4)`
					args = append(args, createdAt, parts[1])
				}
			}
		}
	}

	query += ` ORDER BY p.created_at DESC, p.post_id DESC LIMIT $` + strconv.Itoa(len(args)+1)
	args = append(args, limit)

	rows, err := h.DB.Query(r.Context(), query, args...)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "db_error"})
		return
	}
	defer rows.Close()

	var posts []models.PostResponse

	for rows.Next() {
		var post models.PostResponse
		err = rows.Scan(&post.PostID, &post.ParentPostID, &post.AuthorID, &post.Content, 
			&post.CreatedAt, &post.LikeCount, &post.CommentCount, &post.LikedByMe)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(map[string]string{"error": "scan_error"})
			return
		}
		posts = append(posts, post)
	}

	if posts == nil {
		posts = []models.PostResponse{}
	}

	var nextCursor *string
	if len(posts) == limit {
		lastPost := posts[len(posts)-1]
		cursorStr := base64.URLEncoding.EncodeToString(
			[]byte(lastPost.CreatedAt.Format(time.RFC3339Nano) + "|" + lastPost.PostID))
		nextCursor = &cursorStr
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(models.PostListResponse{
		Posts:      posts,
		NextCursor: nextCursor,
	})
}

// GET /user/liked_posts
func (h *Handler) UserLikedPosts(w http.ResponseWriter, r *http.Request) {
	buf := make([]byte, 1)
	n, _ := r.Body.Read(buf)
	if n > 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "body_must_be_null"})
		return
	}

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

	query := `
		SELECT p.post_id, p.parent_post_id, p.author_id, p.content, p.created_at, p.like_count, p.comment_count,
		EXISTS(SELECT 1 FROM likes l2 WHERE l2.post_id = p.post_id AND l2.user_id = $1) as liked_by_me,
		l.created_at as liked_at
		FROM posts p
		JOIN likes l ON p.post_id = l.post_id
		WHERE l.user_id = $2`
	
	args := []interface{}{authID, userID}
	
	if cursor != "" {
		decodedBytes, err := base64.URLEncoding.DecodeString(cursor)
		if err == nil {
			parts := strings.SplitN(string(decodedBytes), "|", 2)
			if len(parts) == 2 {
				likedAt, parseErr := time.Parse(time.RFC3339Nano, parts[0])
				if parseErr == nil {
					query += ` AND (l.created_at, l.post_id) < ($3, $4)`
					args = append(args, likedAt, parts[1])
				}
			}
		}
	}

	query += ` ORDER BY l.created_at DESC, l.post_id DESC LIMIT $` + strconv.Itoa(len(args)+1)
	args = append(args, limit)

	rows, err := h.DB.Query(r.Context(), query, args...)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "db_error"})
		return
	}
	defer rows.Close()

	var posts []models.PostResponse
	var lastLikedAt time.Time

	for rows.Next() {
		var post models.PostResponse
		var likedAt time.Time
		err = rows.Scan(&post.PostID, &post.ParentPostID, &post.AuthorID, &post.Content, 
			&post.CreatedAt, &post.LikeCount, &post.CommentCount, &post.LikedByMe, &likedAt)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(map[string]string{"error": "scan_error"})
			return
		}
		posts = append(posts, post)
		lastLikedAt = likedAt
	}

	if posts == nil {
		posts = []models.PostResponse{}
	}

	var nextCursor *string
	if len(posts) == limit {
		lastPost := posts[len(posts)-1]
		cursorStr := base64.URLEncoding.EncodeToString(
			[]byte(lastLikedAt.Format(time.RFC3339Nano) + "|" + lastPost.PostID))
		nextCursor = &cursorStr
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(models.PostListResponse{
		Posts:      posts,
		NextCursor: nextCursor,
	})
}