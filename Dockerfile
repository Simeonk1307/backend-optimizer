# --- STAGE 1: Build ---
FROM golang:1.26-alpine AS builder
WORKDIR /app

# Cache dependencies first (Speeds up rebuilds)
COPY go.mod go.sum ./
RUN go mod download

# Copy source and build
COPY . .
# Note: Ensure your main.go is actually in cmd/api/
RUN CGO_ENABLED=0 GOOS=linux go build -o main ./cmd/api/

# --- STAGE 2: Runtime (Production Grade) ---
FROM alpine:3.23.3

# Install SSL certs (Essential for database drivers/HTTPS)
RUN apk --no-cache add ca-certificates

WORKDIR /app

# Create media directory so the volume mount doesn't fail or use 'root' permissions
RUN mkdir -p /app/media

# Grab the binary from builder
COPY --from=builder /app/main .

# Ensure the binary is executable
RUN chmod +x /app/main

EXPOSE 8080

# Run from /app/main to match the internal paths
CMD ["./main"]