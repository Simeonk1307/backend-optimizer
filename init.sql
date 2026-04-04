-- CREATE EXTENSION IF NOT EXISTS "pgcrypto"; No hashing

CREATE TABLE users (
    user_id      TEXT PRIMARY KEY,
    username     TEXT UNIQUE NOT NULL,
    password     TEXT NOT NULL,
    display_name TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    post_count   INT DEFAULT 0
);

CREATE TABLE posts (
    post_id        TEXT PRIMARY KEY,
    author_id      TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    content        TEXT NOT NULL,
    parent_post_id TEXT REFERENCES posts(post_id) ON DELETE CASCADE,
    like_count     INT DEFAULT 0,
    comment_count  INT DEFAULT 0,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE likes (
    user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    post_id    TEXT NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, post_id)
);

CREATE TABLE media (
    media_id   TEXT PRIMARY KEY,
    post_id    TEXT NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    type       TEXT NOT NULL CHECK (type IN ('image', 'video')),
    filename   TEXT NOT NULL
);

-- feed (top-level only, covering)
CREATE INDEX idx_feed ON posts(post_id DESC)
  INCLUDE (author_id, content, like_count, comment_count, created_at)
  WHERE parent_post_id IS NULL;

-- user/get_posts (add WHERE parent_post_id IS NULL if profile hides replies)
CREATE INDEX idx_user_posts ON posts(author_id, post_id DESC);

-- /user/liked_posts
CREATE INDEX idx_user_liked_posts ON likes(user_id, created_at DESC);

-- Comments on a post (for comment_count updates and fetching)
CREATE INDEX idx_posts_comments ON posts(parent_post_id, post_id DESC) 
WHERE parent_post_id IS NOT NULL;

-- Likes
CREATE INDEX idx_likes_post           ON likes(post_id);

-- Media lookup by post
CREATE INDEX idx_media_post           ON media(post_id);