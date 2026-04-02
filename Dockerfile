# --- STAGE 1: The Build Environment ---
# Uses Go 1.26 on Alpine Linux. Alias 'builder' allows Stage 2 to pull files from here.
FROM golang:1.26-alpine AS builder

# Creates '/app' inside the container and 'cd's into it. All following paths are relative to this.
WORKDIR /app

# Copies dependency manifests from your Arch machine to '/app/'. 
# Done separately to cache 'go mod download' and speed up future builds.
COPY go.mod go.sum ./

# Downloads all external Go libraries into the container's module cache.
RUN go mod download

# Copies all remaining source code from your local folder into '/app/'.
COPY . .

# Compiles the app. 
# CGO_ENABLED=0: Disables C-links to make the binary "Static" (runs anywhere).
# GOOS=linux: Ensures the executable works on Linux kernels.
RUN CGO_ENABLED=0 GOOS=linux go build -o main ./cmd/api/


# --- STAGE 2: The Lean Runtime ---
# Starts a fresh, tiny Linux image. We throw away the Go compiler and source code here.
FROM alpine:3.23.3

# Sets the execution directory to the root user's home.
WORKDIR /root/
# media directory needs to exist
RUN mkdir -p media
# Reaches into the 'builder' stage and grabs ONLY the finished 'main' binary.
# This reduces your image size from ~300MB down to ~15MB.
COPY --from=builder /app/main .

# Documentation: Tells Docker the app listens on 8080. (Does not actually open ports).
EXPOSE 8080

# The "Entrypoint": Runs the binary the moment the container starts.
CMD ["./main"]