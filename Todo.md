# Todo

## 1. Cai thien logic san pham tong the

- [ ] Ra soat lai luong end-to-end: guest upload feedback -> clean PII -> classify topic/sentiment/severity -> route team -> tao ticket/alert -> dashboard realtime.
- [ ] Chuan hoa schema du lieu feedback, alert, ticket, agent_run_log va profile de frontend/backend dung cung mot contract.
- [ ] Tach ro 3 lop logic: ingestion/classification, agent reasoning, ticket workflow.
- [ ] Them idempotency key cho feedback va ticket de tranh tao trung khi user upload lai hoac scheduler chay lai.
- [ ] Chuan hoa severity P1-P5 va escalation WATCH/WARNING/CRITICAL, tranh moi noi tinh mot kieu.
- [ ] Them audit log cho cac hanh dong quan trong: upload feedback, sua nhan AI, tao ticket, doi status ticket, agent run.
- [ ] Chuan hoa error handling: loi Supabase, loi LLM, loi model ML, loi upload file, loi auth/permission.
- [ ] Them fallback mode khi thieu API key LLM hoac backend agent loi, de dashboard van chay duoc.
- [ ] Them test cho cac case nghiep vu quan trong thay vi chi test UI thu cong.

## 2. Phan quyen tai khoan

- [ ] Xac dinh cac loai tai khoan trong he thong: admin, manager, staff, guest.
- [ ] Them truong role trong `profiles` va dong bo voi Supabase Auth.
- [ ] Them logic nhan dien tai khoan khach o frontend va backend.
- [ ] Gioi han menu, route va thao tac theo tung loai tai khoan.
- [ ] Dam bao tai khoan khach khong truy cap duoc cac chuc nang quan tri hoac du lieu nhay cam.
- [ ] Them Supabase RLS policy theo role, khong chi chan bang UI.

## 3. Tai khoan khach

- [ ] Tai khoan khach chi duoc xem dashboard.
- [ ] Tai khoan khach chi duoc tai len feedback.
- [ ] Tai khoan khach khong duoc xem danh sach feedback raw neu co du lieu noi bo/PII.
- [ ] Tai khoan khach khong duoc vao Alerts/Ticket Triage, Chat AI, Agent Logs, Admin/Settings.
- [ ] An hoac vo hieu hoa cac nut hanh dong khong danh cho tai khoan khach.
- [ ] Kiem tra dieu huong truc tiep bang URL de tranh truy cap trai phep.
- [ ] Hien thi thong bao phu hop khi tai khoan khach khong co quyen truy cap.

## 4. Dashboard

- [ ] Xac dinh noi dung dashboard ma tai khoan khach duoc phep xem.
- [ ] Tach dashboard public/guest va dashboard noi bo neu can.
- [ ] An cac thong tin noi bo, cau hinh he thong, LLM prompt, service status va thao tac quan tri khoi dashboard guest.
- [ ] Dam bao dashboard hien KPI, trend, severity, area heatmap va alert summary o muc da duoc phep.
- [ ] Kiem tra realtime subscription khong leak du lieu ngoai quyen cua guest.
- [ ] Kiem tra dashboard tren desktop va mobile.
- [ ] Dam bao dashboard van tai dung va khong loi khi nguoi dung la tai khoan khach.

## 5. Feedback upload

- [ ] Tao hoac cap nhat man hinh tai len feedback cho guest.
- [ ] Ho tro nhap feedback text don le.
- [ ] Ho tro upload file CSV/XLSX neu dung scope demo/san pham.
- [ ] Kiem tra dinh dang file, dung luong file, so dong toi da va cac cot bat buoc.
- [ ] Clean PII truoc khi luu hoac truoc khi day vao dashboard noi bo.
- [ ] Luu feedback kem user_id, source, channel, area, timestamp, upload_batch_id va trang thai xu ly.
- [ ] Hien thi trang thai upload thanh cong, dang xu ly, loi validation, loi server.
- [ ] Khong cho guest sua nhan AI hoac sua feedback sau khi gui neu chua co yeu cau nghiep vu ro.

## 6. Build lai he thong 6 agent

- [ ] Chot lai kien truc 6 agent moi va cap nhat `MASTER_BLUEPRINT.md` tu 5 agent thanh 6 agent.
- [ ] Agent 1 - Ingestion/Classifier Agent: nhan feedback moi, clean PII, chay ML topic/sentiment/severity, ap rule safety keyword.
- [ ] Agent 2 - Router Agent: route ticket ve dung team dua tren `routing_table.json`, SLA, severity override P5 -> Safety.
- [ ] Agent 3 - Ticket Agent: tao/cap nhat ticket, dedup ticket trung, gan SLA, owner/team, status va priority.
- [ ] Agent 4 - Insight Agent: tong hop insight theo phong ban, trend, top topic, khu vuc nong, ti le negative, ticket status.
- [ ] Agent 5 - Analyst Agent: phan tich root cause bang LLM, du bao 24-48h, de xuat 3 action co deadline.
- [ ] Agent 6 - Alert/Escalation Agent: phat hien spike, phan cap WATCH/WARNING/CRITICAL, cooldown, escalation khi qua SLA.
- [ ] Orchestrator khong tinh la agent nghiep vu; chi dieu phoi pipeline, retry, logging va schedule.
- [ ] Dinh nghia input/output schema rieng cho tung agent bang dataclass/Pydantic.
- [ ] Moi agent phai co fallback heuristic/mock khi LLM hoac external service loi.
- [ ] Moi agent phai ghi `agent_run_log`: run_id, agent_name, input_hash, output_summary, status, latency_ms, error.
- [ ] Them unit test cho tung agent va integration test cho ca pipeline 6 agent.

## 7. Build lai co che ticket trigger

- [ ] Tach trigger ticket ra khoi logic stream de tranh moi batch deu tao ticket lung tung.
- [ ] Thiet ke trigger theo event: feedback moi P4/P5, spike theo area/topic, upload batch hoan tat, scheduler dinh ky, manual trigger cho demo.
- [ ] Them bang hoac queue `ticket_trigger_events` neu can de luu event can xu ly.
- [ ] Them dieu kien dedup: cung area + topic + severity trong cooldown thi cap nhat ticket cu thay vi tao ticket moi.
- [ ] Them cooldown rieng cho ticket va alert, khong dung chung mot logic mo ho.
- [ ] Them priority scoring: severity, so luong feedback, toc do tang, topic safety, area hot, SLA risk.
- [ ] Them state machine cho ticket: open -> triaged -> in_progress -> waiting -> resolved -> closed.
- [ ] Them SLA logic: due_at, breached_at, escalation_level, assigned_team.
- [ ] Khi feedback duoc upload, trigger chi danh dau can xu ly; agent worker moi tao ticket sau khi gom ngu can thiet.
- [ ] Manual trigger `/api/agent/run` chi dung cho demo/admin, khong mo cho guest.
- [ ] Them test de dam bao trigger khong tao ticket trung khi scheduler/manual trigger chay lien tiep.

## 8. Backend va bao mat

- [ ] Kiem tra lai API de chi cho phep tai khoan khach goi endpoint dashboard duoc phep va endpoint feedback upload.
- [ ] Them middleware hoac dependency auth/role cho FastAPI neu backend co endpoint rieng.
- [ ] Dam bao validate quyen o backend va Supabase RLS, khong chi dua vao giao dien.
- [ ] Ghi log cac lan tai khoan khach bi tu choi truy cap.
- [ ] Chan guest goi cac endpoint trigger demo, trigger spike, agent run, agent chat, ticket status update.
- [ ] Kiem tra service_role key chi nam o server/pipeline, khong bao gio lo ra frontend.
- [ ] Them rate limit cho guest upload feedback de tranh spam.
- [ ] Them test cho cac truong hop tai khoan khach truy cap sai quyen.

## 9. Frontend can cai thien

- [ ] AppShell hien menu theo role, khong hien route guest khong duoc vao.
- [ ] Them guard cho route theo role, khong chi dua vao sidebar.
- [ ] Feedback page tach mode guest upload va mode staff/admin review.
- [ ] Alerts/Ticket page them bo loc team, severity, SLA, status, created_at.
- [ ] Dashboard them empty/loading/error state ro rang.
- [ ] Dashboard va ticket phai doc du lieu realtime nhung khong reload/thay doi layout qua manh.
- [ ] Them toast/log UI khi agent run loi hoac ticket trigger bi fail.
- [ ] Kiem tra responsive mobile cho dashboard, upload feedback va ticket triage.

## 10. Database va Supabase

- [ ] Cap nhat migration cho roles, tickets, ticket_trigger_events, agent_run_logs neu chua co.
- [ ] Them index cho feedback: created_at, area, topic, sentiment, severity, upload_batch_id.
- [ ] Them index cho tickets: status, assigned_team, severity, due_at, dedup_key.
- [ ] Them unique constraint hoac dedup_key de tranh ticket trung.
- [ ] Bat RLS cho cac bang co du lieu nguoi dung.
- [ ] Viet policy guest chi insert feedback cua minh va chi read dashboard view duoc phep.
- [ ] Tao view rieng cho dashboard guest neu can an du lieu raw.

## 11. Kiem thu

- [ ] Test dang nhap bang tai khoan guest.
- [ ] Test guest xem dashboard.
- [ ] Test guest tai len feedback text.
- [ ] Test guest upload file feedback.
- [ ] Test guest truy cap cac trang khong duoc phep bang URL truc tiep.
- [ ] Test user/staff/admin de dam bao khong bi anh huong.
- [ ] Test 6 agent voi data mau va data rong.
- [ ] Test ticket trigger: manual, scheduler, feedback P5, spike theo area/topic, duplicate trigger.
- [ ] Test RLS bang Supabase client voi role guest/user/admin.
- [ ] Test build frontend va smoke test backend truoc khi deploy.

## 12. Tai lieu va demo

- [ ] Cap nhat `README.md` theo flow moi: role guest, 6 agent, ticket trigger, deploy URL.
- [ ] Cap nhat `MASTER_BLUEPRINT.md` theo kien truc 6 agent moi.
- [ ] Cap nhat `RUN.md` voi lenh chay backend/frontend/Supabase va cach trigger demo.
- [ ] Cap nhat demo script: guest upload feedback -> agent xu ly -> ticket/alert hien realtime -> staff resolve.
- [ ] Ghi ro bien moi truong can co trong `.env.example`.

## 13. Dua len URL public de moi nguoi truy cap

- [ ] Chon phuong an deploy frontend: Vercel/Netlify/Render static.
- [ ] Chon phuong an deploy backend pipeline/API: Railway/Render/Fly.io hoac Supabase Edge neu phu hop.
- [ ] Cau hinh Supabase remote project, Auth redirect URL va RLS cho moi truong production.
- [ ] Cau hinh environment variables tren hosting, khong dung `.env` local.
- [ ] Doi `VITE_BACKEND_API_URL` va Supabase URL/key sang endpoint production.
- [ ] Kiem tra CORS cho backend production.
- [ ] Kiem tra scheduler/worker agent chay tren moi truong deploy, khong phu thuoc may local.
- [ ] Tao URL public cho frontend de moi nguoi co the vao dung.
- [ ] Smoke test tren URL public: login guest, xem dashboard, upload feedback, agent/ticket chay dung.
- [ ] Cap nhat `README.md` va `RUN.md` voi link URL public va cach van hanh production.
