package handlers

import (
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

type Handler struct {
	DB    *pgxpool.Pool
	Redis *redis.Client
}

// NewHandler is the "Constructor" — it injects the dependencies
func NewHandler(db *pgxpool.Pool, rd *redis.Client) *Handler {
	return &Handler{
		DB:    db,
		Redis: rd,
	}
}