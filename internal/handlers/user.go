package handlers

import (
	"encoding/json"
	"io"
	"net/http"

	"backend-optimizer/internal/middleware"
	"backend-optimizer/internal/models"
)

// GET /user/details
func (h *Handler) UserDetails(w http.ResponseWriter, r *http.Request) {
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

	var res models.UserDetailResponse
	err := h.DB.QueryRow(r.Context(), 
		"SELECT user_id, username, display_name, post_count FROM users WHERE user_id = $1", 
		userID).Scan(&res.UserID, &res.Username, &res.DisplayName, &res.PostCount)
	
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "user_not_found"})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(res)
}

// POST /user/delete
func (h *Handler) UserDelete(w http.ResponseWriter, r *http.Request) {
	// Read and validate body is exactly {}
	body, err := io.ReadAll(r.Body)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "invalid_request_body"})
		return
	}

	// Check if body is valid JSON and is an empty object
	var emptyObj map[string]interface{}
	if err := json.Unmarshal(body, &emptyObj); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "invalid_request_body"})
		return
	}

	// Ensure the object is empty (no fields)
	if len(emptyObj) != 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "invalid_request_body"})
		return
	}

	userID := middleware.UserIDFromCtx(r.Context())

	// Perform the deletion
	res, err := h.DB.Exec(r.Context(), "DELETE FROM users WHERE user_id = $1", userID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]string{"error": "delete_failed"})
		return
	}

	if res.RowsAffected() == 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "user_not_found"})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]bool{"success": true})
}