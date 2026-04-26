import React from 'react';
import { MarkdownBlock, MetricBlock, TableBlock, ChartBlock, EmbedBlock } from './DynamicBlocks';

// Map type ที่ได้รับจาก JSON เข้ากับ React Component
const BlockMap = {
  markdown: MarkdownBlock,
  metric: MetricBlock,
  table: TableBlock,
  chart: ChartBlock,
  embed: EmbedBlock
};

// 🚀 ทริคแก้ปัญหา Tailwind Purge: เขียน Mapping Class ไว้ล่วงหน้า
// ห้ามต่อ String แบบ `md:col-span-${colSpan}` เด็ดขาด!
const colSpanClasses = {
  1: "md:col-span-1",
  2: "md:col-span-2",
  3: "md:col-span-3",
  4: "md:col-span-4",
  5: "md:col-span-5",
  6: "md:col-span-6",
  7: "md:col-span-7",
  8: "md:col-span-8",
  9: "md:col-span-9",
  10: "md:col-span-10",
  11: "md:col-span-11",
  12: "md:col-span-12"
};

export default function DynamicWidgetRenderer({ blocks }) {
  // หากไม่มีข้อมูล ให้เรนเดอร์หน้าเปล่า
  if (!blocks || !Array.isArray(blocks) || blocks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-gray-50 border border-dashed border-gray-300 rounded-xl">
        <p className="text-gray-400 font-medium text-sm">ยังไม่มีผลการวิเคราะห์</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-12 gap-4 w-full">
      {blocks.map((block, index) => {
        const TargetComponent = BlockMap[block.type];
        
        // กำหนดความกว้างของการ์ด (Grid System) 
        const colSpan = block.colSpan || 12;
        
        // 🚀 ดึง Class จาก Object Mapping ที่สร้างไว้
        const gridClass = `col-span-1 ${colSpanClasses[colSpan] || "md:col-span-12"}`;

        if (!TargetComponent) {
          console.warn(`Unsupported block type: ${block.type}`);
          return null; 
        }

        return (
          <div key={block.id || index} className={gridClass}>
            <TargetComponent payload={block} />
          </div>
        );
      })}
    </div>
  );
}