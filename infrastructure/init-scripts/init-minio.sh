#!/bin/sh

echo "Waiting for MinIO to start..."

# พยายามเชื่อมต่อจนกว่า MinIO จะพร้อม
until (/usr/bin/mc alias set myminio http://minio:9000 admin password123) do 
    echo '...waiting for MinIO...' 
    sleep 1
done

echo "MinIO is ready! Creating buckets and paths according to Project Plan..."

# ==========================================
# 1. Bucket: ai-tool-scripts
# ==========================================
/usr/bin/mc mb --ignore-existing myminio/ai-tool-scripts
echo "Creating sub-folders for ai-tool-scripts..."
echo "" | /usr/bin/mc pipe myminio/ai-tool-scripts/traditional-logic/.keep
echo "" | /usr/bin/mc pipe myminio/ai-tool-scripts/ai-inference/.keep
echo "" | /usr/bin/mc pipe myminio/ai-tool-scripts/sandbox-temp/.keep
echo "" | /usr/bin/mc pipe myminio/ai-tool-scripts/external-apis/.keep

# ==========================================
# 2. Bucket: raw-data (Bronze Layer)
# ==========================================
/usr/bin/mc mb --ignore-existing myminio/raw-data
echo "Creating sub-folders for raw-data..."
echo "" | /usr/bin/mc pipe myminio/raw-data/financial-statements/.keep
echo "" | /usr/bin/mc pipe myminio/raw-data/stock-prices/.keep
echo "" | /usr/bin/mc pipe myminio/raw-data/news/.keep

# ==========================================
# 3. Bucket: processed-data (Silver/Gold Layer)
# ==========================================
/usr/bin/mc mb --ignore-existing myminio/processed-data
echo "Creating sub-folders for processed-data..."
echo "" | /usr/bin/mc pipe myminio/processed-data/clean-financials/.keep
echo "" | /usr/bin/mc pipe myminio/processed-data/aggregated-prices/.keep

echo "✅ All buckets and paths successfully created!"