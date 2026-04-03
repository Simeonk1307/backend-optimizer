CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
    user_id      TEXT PRIMARY KEY DEFAULT 'u_' || gen_random_uuid(),
    username     TEXT UNIQUE NOT NULL,
    password     TEXT NOT NULL,
    display_name TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE posts (
    post_id        TEXT PRIMARY KEY DEFAULT 'p_' || gen_random_uuid(),
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
    media_id   TEXT PRIMARY KEY DEFAULT 'm_' || gen_random_uuid(),
    post_id    TEXT NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    type       TEXT NOT NULL CHECK (type IN ('image', 'video')),
    filename   TEXT NOT NULL
);

-- Feed: posts by time (top-level only for main feed)
CREATE INDEX idx_posts_created        ON posts(created_at DESC) WHERE parent_post_id IS NULL;
-- User posts
CREATE INDEX idx_posts_author         ON posts(author_id, created_at DESC);
-- Comments on a post (for comment_count updates and fetching)
CREATE INDEX idx_posts_parent         ON posts(parent_post_id) WHERE parent_post_id IS NOT NULL;
-- Likes
CREATE INDEX idx_likes_user           ON likes(user_id);
CREATE INDEX idx_likes_post           ON likes(post_id);
-- Media lookup by post
CREATE INDEX idx_media_post           ON media(post_id);