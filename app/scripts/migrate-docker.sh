#!/bin/bash
# Run migrations from inside Docker container
# Usage: ./scripts/migrate-docker.sh

MIGRATIONS_DIR="../supabase/migrations"

for file in $(ls $MIGRATIONS_DIR/*.sql | sort); do
  echo "Running migration: $(basename $file)"
  docker exec -i lola-postgres psql -U lola -d lola_db < "$file"
  if [ $? -eq 0 ]; then
    echo "✓ Successfully applied: $(basename $file)"
  else
    echo "✗ Error applying: $(basename $file)"
  fi
done

echo "Migration complete!"

