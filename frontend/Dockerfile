# ใช้ Node.js เป็น Base Image (เลือกเวอร์ชัน alpine เพื่อความเบา)
FROM node:20-alpine

# กำหนด Working Directory ภายใน Container
WORKDIR /app

# คัดลอกไฟล์ package.json และ package-lock.json เข้าไปก่อนเพื่อ Install Dependencies
# (ช่วยเรื่อง Caching ให้บิลด์เร็วขึ้นในครั้งถัดไป)
COPY frontend/package*.json ./

# ติดตั้ง Packages
RUN npm install

# คัดลอก Source Code ทั้งหมด
COPY frontend/ .

# เปิดพอร์ต 5173 ซึ่งเป็นพอร์ตเริ่มต้นของ Vite
EXPOSE 5173

# สั่งรัน Vite โดยใส่ flag --host เพื่อให้สามารถเข้าถึงได้จากภายนอก Container
CMD ["npm", "run", "dev", "--", "--host"]