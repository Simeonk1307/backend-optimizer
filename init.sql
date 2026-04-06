CREATE TABLE users (
    user_id      TEXT PRIMARY KEY,
    username     TEXT UNIQUE NOT NULL,
    password     TEXT NOT NULL,
    display_name TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    post_count   INT DEFAULT 0 CHECK (post_count >= 0),
    
    -- Strict Logic Checks
    CONSTRAINT ck_user_id_format      CHECK (user_id LIKE 'u_%'),
    CONSTRAINT ck_username_length     CHECK (length(btrim(username)) >= 1),
    CONSTRAINT ck_password_length     CHECK (length(btrim(password)) >= 1),
    CONSTRAINT ck_display_name_length CHECK (length(btrim(display_name)) >= 1)
);

CREATE TABLE posts (
    post_id        TEXT PRIMARY KEY,
    author_id      TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    content        TEXT NOT NULL,
    parent_post_id TEXT REFERENCES posts(post_id) ON DELETE CASCADE,
    like_count     INT DEFAULT 0 CHECK (like_count >= 0),
    comment_count  INT DEFAULT 0 CHECK (comment_count >= 0),
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    
    -- Content cannot be empty string or just whitespace
    CONSTRAINT ck_post_id_format   CHECK (post_id LIKE 'p_%'),
    CONSTRAINT ck_content_not_empty CHECK (length(btrim(content)) > 0)
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
    filename   TEXT NOT NULL,
    
    CONSTRAINT ck_media_id_format CHECK (media_id LIKE 'm_%'),
    CONSTRAINT ck_filename_not_empty CHECK (length(btrim(filename)) > 0)
);

-- Feed index (top-level posts only, ordered by time)
CREATE INDEX idx_feed ON posts(created_at DESC, post_id DESC)
  INCLUDE (author_id, content, like_count, comment_count, parent_post_id)
  WHERE parent_post_id IS NULL;

-- User posts index (matches ORDER BY created_at DESC, post_id DESC)
CREATE INDEX idx_user_posts ON posts(author_id, created_at DESC, post_id DESC);

-- User liked posts index (matches ORDER BY l.created_at DESC, l.post_id DESC)
CREATE INDEX idx_user_liked_posts ON likes(user_id, created_at DESC, post_id DESC);

-- Comments on a post (for comment_count updates and fetching)
CREATE INDEX idx_posts_comments ON posts(parent_post_id, post_id DESC) 
  WHERE parent_post_id IS NOT NULL;

-- Likes lookup optimized for EXISTS(... WHERE post_id = ? AND user_id = ?)
CREATE INDEX idx_likes_post_user ON likes(post_id, user_id);

-- Media lookup by post
CREATE INDEX idx_media_post ON media(post_id);

-- Trigger function to maintain post_count
CREATE OR REPLACE FUNCTION update_post_count() RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE users SET post_count = post_count + 1 WHERE user_id = NEW.author_id;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE users SET post_count = post_count - 1 WHERE user_id = OLD.author_id;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_post_count
AFTER INSERT OR DELETE ON posts
FOR EACH ROW EXECUTE FUNCTION update_post_count();

-- Trigger function to maintain like_count
CREATE OR REPLACE FUNCTION update_like_count() RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE posts SET like_count = like_count + 1 WHERE post_id = NEW.post_id;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE posts SET like_count = like_count - 1 WHERE post_id = OLD.post_id;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_like_count
AFTER INSERT OR DELETE ON likes
FOR EACH ROW EXECUTE FUNCTION update_like_count();

-- Trigger function to maintain comment_count
CREATE OR REPLACE FUNCTION update_comment_count() RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' AND NEW.parent_post_id IS NOT NULL THEN
    UPDATE posts SET comment_count = comment_count + 1 WHERE post_id = NEW.parent_post_id;
  ELSIF TG_OP = 'DELETE' AND OLD.parent_post_id IS NOT NULL THEN
    UPDATE posts SET comment_count = comment_count - 1 WHERE post_id = OLD.parent_post_id;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_comment_count
AFTER INSERT OR DELETE ON posts
FOR EACH ROW EXECUTE FUNCTION update_comment_count();