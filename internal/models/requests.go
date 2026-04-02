package models

// ########## AUTH ###########
// POST /auth/register
type RegisterRequest struct {
    Username    string `json:"username"`
    Password    string `json:"password"`
    DisplayName string `json:"display_name"`
}

// POST /auth/login
type LoginRequest struct {
    Username string `json:"username"`
    Password string `json:"password"`
}

// ########## POSTS ###############
// POST /posts/delete
type PostDeleteRequest struct {
    PostID string `json:"post_id"`
}

// POST /posts/like
type PostLikeRequest struct {
    PostID string `json:"post_id"`
    Liked  bool   `json:"liked"`
}