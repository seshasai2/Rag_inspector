#!/usr/bin/env bash
set -e

echo "🚀 RAGInspector Setup"
echo "===================="

# Check dependencies
command -v docker >/dev/null 2>&1 || { echo "❌ Docker required. Install: https://docs.docker.com/get-docker/"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || command -v docker >/dev/null 2>&1 || { echo "❌ Docker Compose required."; exit 1; }

# Create .env if not exists
if [ ! -f .env ]; then
  echo "📝 Creating .env from template..."
  cp .env.example .env
  # Generate a random SECRET_KEY (must match placeholder in .env.example)
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))" 2>/dev/null || openssl rand -hex 32)
  # Must match SECRET_KEY placeholder in .env.example
  PLACEHOLDER='change-me-generate-a-32-plus-char-secret'
  if grep -q "$PLACEHOLDER" .env; then
    # GNU sed (Linux) and BSD sed (macOS)
    if sed --version >/dev/null 2>&1; then
      sed -i "s/${PLACEHOLDER}/${SECRET_KEY}/" .env
    else
      sed -i '' "s/${PLACEHOLDER}/${SECRET_KEY}/" .env
    fi
  else
    echo "⚠️  SECRET_KEY placeholder not found in .env — set SECRET_KEY manually."
  fi
  echo "✅ .env created. Edit it to add your Razorpay keys."
else
  echo "✅ .env already exists."
fi

echo ""
echo "📦 Building Docker images..."
docker compose build

echo ""
echo "🗄️  Starting database and Redis..."
docker compose up -d db redis

echo ""
echo "⏳ Waiting for database to be ready..."
sleep 8

echo ""
echo "🔄 Running database migrations..."
docker compose run --rm backend alembic upgrade head

echo ""
echo "🚀 Starting all services..."
docker compose up -d

echo ""
echo "✅ RAGInspector is running!"
echo ""
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "📖 Next steps:"
echo "   1. Seed demo data: docker compose run --rm backend python scripts/seed_demo.py"
echo "   2. Open http://localhost:3000 — login demo@example.com / DemoPass123!"
echo "   3. Read docs/DEVELOPER.md and CONTRIBUTING.md"
echo "   4. (Optional) Ollama: https://ollama.ai then ollama pull llama3.2:3b"
echo "   5. (Optional) Add Razorpay keys to .env for billing"
echo ""
