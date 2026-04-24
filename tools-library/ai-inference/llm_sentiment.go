#!/bin/bash
# สคริปต์จำลองการทำงานของ AI Inference Agent

# วนลูปอ่านค่า Argument ที่ Airflow ส่งมาให้ (เช่น --system_prompt)
while [ $# -gt 0 ]; do
  case "$1" in
    --system_prompt)
      PROMPT="$2"
      shift 2
      ;;
    --output_path)
      OUTPUT_PATH="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

echo "🤖 [AI Agent] Initializing LLM Model..."
echo "🧠 System Prompt: $PROMPT"
echo "📊 Analyzing sentiment from ETL data..."

# จำลองผลลัพธ์
echo '{"status": "success", "sentiment": "Bullish", "confidence": 0.95}' > /tmp/result.json

echo "✅ Analysis complete! Output saved (simulated) to $OUTPUT_PATH"