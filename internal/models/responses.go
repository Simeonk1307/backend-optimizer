package models

import "time"

// ########## AUTH ##############
// POST /auth/register
type RegisterResponse struct {
    UserID      string `json:"user_id"`
    Username    string `json:"username"`
    DisplayName string `json:"display_name"`
    Token       string `json:"token"`
}

// POST /auth/login
type LoginResponse struct {
    UserID string `json:"user_id"`
    Token  string `json:"token"`
}

// ############ USER #############
// GET /user/details
type UserDetailResponse struct {
    UserID      string `json:"user_id"`
    Username    string `json:"username"`
    DisplayName string `json:"display_name"`
    PostCount   int    `json:"post_count"`
}

// POST /user/delete
type UserDeleteResponse struct {
	Success bool `json:"success"`
}

// Optimization: When you convert time.Time to string in your handlers, ensure you use time.RFC3339 (e.g., 2026-03-29T09:00:00Z). 
// The benchmark tool is usually very picky about the "Z" suffix for UTC.
// Reusable post shape for lists (get_posts, liked_posts, feed)
type PostResponse struct {
    PostID       string  `json:"post_id"`
    AuthorID     string    `json:"author_id"`
    ParentPostID *string   `json:"parent_post_id"`
    Content      string    `json:"content"`
    CreatedAt    time.Time `json:"created_at"`
    LikeCount    int       `json:"like_count"`
    CommentCount int       `json:"comment_count"`
    LikedByMe    bool      `json:"liked_by_me"`
}

// GET /user/get_posts and /user/liked_posts
type PostListResponse struct {
    Posts      []PostResponse `json:"posts"`
    NextCursor *string        `json:"next_cursor"`
}

type Cursor struct {
    CreatedAt time.Time `json:"created_at"`
    PostID    string    `json:"post_id"`
}

//  ############# MEDIA ###############
// Returned by /posts/create - no URLs yet
type MediaCreateResponse struct {
    Type    string `json:"type"`
    MediaID string `json:"media_id"`
}

// Returned by /posts/details - full URLs
type MediaDetailResponse struct {
    Type         string `json:"type"`
    MediaID      string `json:"media_id"`
    URL          string `json:"url"`
    ThumbnailURL string `json:"thumbnail_url"`
}


// ################# POSTS ##############
// POST /posts/create
type PostCreateResponse struct {
    PostID       string                `json:"post_id"`
    AuthorID     string                `json:"author_id"`
    ParentPostID *string               `json:"parent_post_id"`
    Content      string                `json:"content"`
    CreatedAt    time.Time             `json:"created_at"`
	Media        []MediaCreateResponse `json:"media"`
}

// GET /posts/details
type PostDetailResponse struct {
    PostID       string                `json:"post_id"`
    AuthorID     string                `json:"author_id"`
    ParentPostID *string               `json:"parent_post_id"`
    Content      string                `json:"content"`
    CreatedAt    time.Time             `json:"created_at"`
    LikeCount    int                   `json:"like_count"`
    CommentCount int                   `json:"comment_count"`
    LikedByMe    bool                  `json:"liked_by_me"`
    Media        []MediaDetailResponse `json:"media"`
}

// POST /posts/delete
type PostDeleteResponse struct {
    Success bool `json:"success"`
}

// POST /posts/like
type PostLikeResponse struct {
    PostID    string `json:"post_id"`
    LikeCount int    `json:"like_count"`
    LikedByMe bool   `json:"liked_by_me"`
}