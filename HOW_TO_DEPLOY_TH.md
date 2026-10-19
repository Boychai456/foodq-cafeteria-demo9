# คู่มือ Deploy FoodQ สำหรับนักศึกษา

## GitHub Pages: เร็วที่สุด (Frontend Demo)
1. ไปที่ https://github.com/new สร้าง Repository ชื่อ `foodq-cafeteria-demo`.
2. แตกไฟล์ ZIP แล้ว Upload **ไฟล์และโฟลเดอร์ทั้งหมดด้านใน** ไปที่ Repository (Add file > Upload files > Commit changes).
3. ไปที่ Settings > Pages > Deploy from a branch > `main` > `/docs` > Save.
4. รอจน GitHub แสดงลิงก์ แล้วเข้า URL ที่แสดงภายใต้ Pages.
5. ทดลองจองคิวได้ทันที **แต่แต่ละเบราว์เซอร์เห็นข้อมูลเฉพาะตัวเอง**.

## Render: Full Stack สำหรับสาธิต
1. หลังขึ้น GitHub แล้ว เปิด https://dashboard.render.com/ และเชื่อม Repository.
2. เลือก New > Web Service > Repository ของ FoodQ.
3. Runtime: Python, Build: `python -m compileall -q server.py`, Start: `python server.py`, Plan: Free (ถ้ามีให้เลือก), Health: `/api/health`.
4. รอ Deploy แล้วเข้า URL `https://...onrender.com` ที่ Render แสดง **URL นี้จะใช้ร่วมกันได้หลายเครื่อง**.
5. ที่หน้าเว็บจะขึ้น `เชื่อมต่อ Backend แล้ว` เมื่อ API ใช้งานได้.

**ข้อควรระวัง:** GitHub ไม่ได้โฮสต์ Python Backend; Render Free เก็บฐานข้อมูล SQLite ชั่วคราวและอาจลบข้อมูลหลังพักระบบ/รีสตาร์ท; เดโมนี้ไม่มี Login/กำหนดสิทธิ์จริง จึงไม่ควรใช้ข้อมูลนักศึกษาจริงหรือข้อมูลส่วนบุคคล.
