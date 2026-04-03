package models

import "time"

type User struct {
    UserID      string    `db:"user_id"`
    Username    string    `db:"username"`
    HashedPassword    string    `db:"hashed_password"`
    DisplayName string    `db:"display_name"`
    CreatedAt   time.Time `db:"created_at"`
}

type Media struct {
    MediaID  string `db:"media_id"`
    PostID   string `db:"post_id"`
    Type     string `db:"type"`
    Filename string `db:"filename"`
}

type Post struct {
    PostID       string    `db:"post_id"`
    AuthorID     string    `db:"author_id"`
    Content      string    `db:"content"`
    LikeCount    int       `db:"like_count"`
    CommentCount int       `db:"comment_count"`
    CreatedAt    time.Time `db:"created_at"`
}

