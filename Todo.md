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

- [x] Xac dinh cac loai tai khoan trong he thong: admin, manager, staff, guest.
- [x] Them truong role trong `profiles` va dong bo voi Supabase Auth.
- [x] Them logic nhan dien tai khoan khach o frontend va backend.
- [x] Gioi han menu, route va thao tac theo tung loai tai khoan.
- [x] Dam bao tai khoan khach khong truy cap duoc cac chuc nang quan tri hoac du lieu nhay cam.
- [ ] Them Supabase RLS policy theo role, khong chi chan bang UI.

## 3. Tai khoan khach

- [x] Tai khoan khach chi duoc xem dashboard.
- [x] Tai khoan khach chi duoc tai len feedback.
- [x] Tai khoan khach khong duoc xem danh sach feedback raw neu co du lieu noi bo/PII.
- [x] Tai khoan khach khong duoc vao Alerts/Ticket Triage, Chat AI, Agent Logs, Admin/Settings.
- [x] An hoac vo hieu hoa cac nut hanh dong khong danh cho tai khoan khach.
- [x] Kiem tra dieu huong truc tiep bang URL de tranh truy cap trai phep.
- [x] Hien thi thong bao phu hop khi tai khoan khach khong co quyen truy cap.

## 4. Dashboard

- [x] Xac dinh noi dung dashboard ma tai khoan khach duoc phep xem.
- [x] Tach dashboard public/guest va dashboard noi bo neu can.
- [x] An cac thong tin noi bo, cau hinh he thong, LLM prompt, service status va thao tac quan tri khoi dashboard guest.
- [ ] Dam bao dashboard hien KPI, trend, severity, area heatmap va alert summary o muc da duoc phep.
- [ ] Kiem tra realtime subscription khong leak du lieu ngoai quyen cua guest.
- [ ] Kiem tra dashboard tren desktop va mobile.
- [x] Dam bao dashboard van tai dung va khong loi khi nguoi dung la tai khoan khach.

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

- [x] Chot lai kien truc 6 agent moi va cap nhat `MASTER_BLUEPRINT.md` tu 5 agent thanh 6 agent.
- [x] Agent 1 - Ingestion/Classifier Agent: nhan feedback moi, clean PII, chay ML topic/sentiment/severity, ap rule safety keyword.
- [x] Agent 2 - Router Agent: route ticket ve dung team dua tren `routing_table.json`, SLA, severity override P5 -> Safety.
- [x] Agent 3 - Ticket Agent: tao/cap nhat ticket, dedup ticket trung, gan SLA, owner/team, status va priority.
- [x] Agent 4 - Insight Agent: tong hop insight theo phong ban, trend, top topic, khu vuc nong, ti le negative, ticket status.
- [x] Agent 5 - Analyst Agent: phan tich root cause bang LLM, du bao 24-48h, de xuat 3 action co deadline.
- [x] Agent 6 - Alert/Escalation Agent: phat hien spike, phan cap WATCH/WARNING/CRITICAL, cooldown, escalation khi qua SLA.
- [x] Orchestrator khong tinh la agent nghiep vu; chi dieu phoi pipeline, retry, logging va schedule.
- [x] Dinh nghia input/output schema rieng cho tung agent bang dataclass/Pydantic.
- [x] Moi agent phai co fallback heuristic/mock khi LLM hoac external service loi.
- [x] Moi agent phai ghi `agent_run_log`: run_id, agent_name, input_hash, output_summary, status, latency_ms, error.
- [ ] Them unit test cho tung agent va integration test cho ca pipeline 6 agent.

## 7. Build lai co che ticket trigger

- [x] Tach trigger ticket ra khoi logic stream de tranh moi batch deu tao ticket lung tung.
- [x] Thiet ke trigger theo event: feedback moi P4/P5, spike theo area/topic, upload batch hoan tat, scheduler dinh ky, manual trigger cho demo.
- [x] Them bang hoac queue `ticket_trigger_events` neu can de luu event can xu ly.
- [x] Them dieu kien dedup: cung area + topic + severity trong cooldown thi cap nhat ticket cu thay vi tao ticket moi.
- [x] Them cooldown rieng cho ticket va alert, khong dung chung mot logic mo ho.
- [x] Them priority scoring: severity, so luong feedback, toc do tang, topic safety, area hot, SLA risk.
- [x] Them state machine cho ticket: open -> triaged -> in_progress -> waiting -> resolved -> closed.
- [x] Them SLA logic: due_at, breached_at, escalation_level, assigned_team.
- [x] Khi feedback duoc upload, trigger chi danh dau can xu ly; agent worker moi tao ticket sau khi gom ngu can thiet.
- [x] Manual trigger `/api/agent/run` chi dung cho demo/admin, khong mo cho guest.
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

## 9. Gom ticket thanh task va bao cao truong phong

- [ ] Thiet ke bang/logic `tasks` de gom nhieu ticket lien quan thanh mot viec can xu ly.
- [ ] Them co che cluster ticket theo team, area, topic, severity, thoi gian va root cause.
- [ ] Moi task can co title, summary, related_ticket_ids, assigned_team, owner, priority, due_at, status.
- [ ] Them logic tu dong gan ticket moi vao task dang mo neu cung van de, thay vi tao task moi.
- [ ] Tao summary cho tung nhom ticket: diem chung, so luong case, muc anh huong, khu vuc, khung gio, quote dai dien.
- [ ] Them report theo phong ban hang ngay/hang tuan cho truong phong.
- [ ] Report can co: top van de, task uu tien, SLA risk, ticket qua han, root cause, action plan, owner de xuat.
- [ ] Cho truong phong duyet/sua task va report truoc khi chia viec cho nhan su.
- [ ] Them trang Department Report de xem bao cao theo team va export Markdown/PDF neu can.
- [ ] Them audit log khi agent gom ticket, tao task, cap nhat task hoac sinh bao cao.

## 10. Kiem soat LLM rate limit va chi phi

- [x] Them LLM gateway/wrapper dung chung cho tat ca agent va chatbot.
- [x] Them retry voi exponential backoff khi gap 429/rate limit.
- [ ] Them queue cho job LLM de khong goi dong loat khi co nhieu ticket.
- [x] Them cache theo input_hash cho cac prompt phan tich giong nhau.
- [x] Gom nhieu ticket thanh batch truoc khi goi LLM, tranh goi tung ticket rieng le.
- [x] Uu tien heuristic/model local cho cac viec don gian; chi goi LLM khi can root cause/report/action plan.
- [ ] Dat budget theo ngay/thang: max requests, max tokens, max cost cho demo va production.
- [x] Them circuit breaker: khi LLM loi lien tiep thi tam dung agent LLM va dung fallback.
- [x] Log token usage, latency, provider, model, cost estimate, status cho moi request.
- [ ] Them man hinh/admin log de xem LLM usage va loi rate limit.

## 11. Cham diem feedback ro rang hon

- [x] Thiet ke rubric cham diem feedback theo cac truc: do nguy hiem, an toan, thai do, anh huong dich vu, do khan cap, do tin cay.
- [x] Tach `severity` khoi cac score chi tiet de tranh mot cot severity phai ganh qua nhieu y nghia.
- [x] Them cac truong diem goi y: `safety_score`, `attitude_score`, `urgency_score`, `impact_score`, `confidence_score`.
- [x] Dinh nghia thang diem 1-5 hoac 0-100 va mapping sang priority/ticket severity.
- [x] Viet rule-based override cho cac keyword nghiem trong: tai nan, say xin, de doa, quay roi, gian lan, mat an toan.
- [x] Cho staff/admin sua diem AI cham sai va luu correction log.
- [ ] Dung correction log de danh gia lai model/rule va cai thien prompt.
- [ ] Hien thi score breakdown trong feedback detail va ticket detail.
- [ ] Them test cho cac case feedback nghiem trong, feedback mo ho, feedback tich cuc nhung co keyword rui ro.

## 12. Dashboard support khach hang online

- [ ] Tao dashboard rieng cho support/CS online de theo doi feedback/ticket dang can phan hoi.
- [ ] Hien hang doi feedback moi theo do khan cap, SLA, kenh gui va khu vuc.
- [ ] Them trang chi tiet khach hang/feedback voi lich su ticket lien quan neu co quyen.
- [ ] Them mau phan hoi/canned response cho cac van de lap lai.
- [ ] Them trang thai support: new, reviewing, replied, waiting_customer, escalated, resolved.
- [ ] Them assignment cho nhan vien support va filter theo nguoi phu trach.
- [ ] Them metric support: first response time, resolution time, backlog, overdue, reopen rate.
- [ ] Tich hop voi ticket/task workflow de support co the escalate len phong ban lien quan.
- [ ] Dam bao dashboard support khong hien PII cho role khong duoc phep.
- [ ] Them realtime update khi feedback moi hoac ticket support doi trang thai.

## 13. Frontend can cai thien

- [x] AppShell hien menu theo role, khong hien route guest khong duoc vao.
- [x] Them guard cho route theo role, khong chi dua vao sidebar.
- [x] Feedback page tach mode guest upload va mode staff/admin review.
- [ ] Alerts/Ticket page them bo loc team, severity, SLA, status, created_at.
- [ ] Dashboard them empty/loading/error state ro rang.
- [ ] Dashboard va ticket phai doc du lieu realtime nhung khong reload/thay doi layout qua manh.
- [ ] Them toast/log UI khi agent run loi hoac ticket trigger bi fail.
- [ ] Kiem tra responsive mobile cho dashboard, upload feedback va ticket triage.

## 14. Database va Supabase

- [ ] Cap nhat migration cho roles, tickets, ticket_trigger_events, agent_run_logs neu chua co.
- [ ] Cap nhat migration cho tasks, task_ticket_links, department_reports, feedback_scores neu can.
- [ ] Them index cho feedback: created_at, area, topic, sentiment, severity, upload_batch_id.
- [ ] Them index cho tickets: status, assigned_team, severity, due_at, dedup_key.
- [ ] Them index cho tasks: assigned_team, owner, priority, due_at, status.
- [ ] Them unique constraint hoac dedup_key de tranh ticket trung.
- [ ] Bat RLS cho cac bang co du lieu nguoi dung.
- [ ] Viet policy guest chi insert feedback cua minh va chi read dashboard view duoc phep.
- [ ] Tao view rieng cho dashboard guest neu can an du lieu raw.

## 15. Kiem thu

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
- [ ] Test gom ticket thanh task va sinh department report.
- [ ] Test LLM rate limit: retry, queue, cache, fallback, circuit breaker.
- [ ] Test feedback scoring voi bo case nghiem trong/khong nghiem trong.
- [ ] Test dashboard support voi role support, manager, guest.

## 16. Tai lieu va demo

- [ ] Cap nhat `README.md` theo flow moi: role guest, 6 agent, ticket trigger, deploy URL.
- [ ] Cap nhat `MASTER_BLUEPRINT.md` theo kien truc 6 agent moi.
- [x] Cap nhat `README.md` voi lenh chay backend/frontend/Supabase va cach trigger demo.
- [ ] Cap nhat demo script: guest upload feedback -> agent xu ly -> ticket/alert hien realtime -> staff resolve.
- [ ] Cap nhat demo script them flow: nhieu ticket -> gom thanh task -> sinh report gui truong phong.
- [ ] Ghi ro chien luoc giam goi LLM/rate limit trong tai lieu ky thuat.
- [ ] Ghi ro rubric cham diem feedback va cach staff sua diem AI.
- [ ] Ghi ro workflow dashboard support online.
- [ ] Ghi ro bien moi truong can co trong `.env.example`.

## 17. Chat AI va RAG

- [ ] Xac dinh Chat AI dung de hoi ve dashboard/ticket/feedback hay hoi tai lieu noi bo.
- [ ] Tach prompt system cho manager, staff va admin neu quyen khac nhau.
- [ ] Khong cho guest dung Chat AI neu co nguy co lo du lieu noi bo.
- [ ] Neu giu Chat AI, backend phai lay du lieu theo role va chi dua context duoc phep vao LLM.
- [ ] Them guard de LLM khong tra ve PII, service_role key, prompt noi bo hoac du lieu raw nhay cam.
- [ ] Luu chat history theo user va them nut xoa lich su neu can.
- [ ] Them logging chi phi/token/latency cho moi request LLM.
- [ ] Them fallback khi LLM timeout hoac het quota.

## 18. Chatbot assistant cho van hanh

- [ ] Dinh nghia chatbot tra loi duoc cac cau hoi nao: "khu vuc nao dang nong", "ticket nao sap qua SLA", "team nao can uu tien".
- [ ] Them tool/function cho chatbot doc dashboard summary, ticket summary va insight summary thay vi doc truc tiep bang query tuy y.
- [ ] Gioi han chatbot chi duoc goi cac tool read-only, khong tu y sua ticket hoac tao alert neu chua co confirm.
- [ ] Neu cho chatbot tao action, bat buoc co confirm step va audit log.
- [ ] Them citation/nguon du lieu cho cau tra loi chatbot: ticket id, alert id, time range.
- [ ] Test chatbot voi cau hoi sai, cau hoi ngoai scope, prompt injection va yeu cau xem du lieu khong co quyen.

## 19. Chatbot public cho guest

- [x] Quyet dinh co can chatbot public cho guest hay khong; neu khong can thi an hoan toan.
- [x] Neu co chatbot guest, chi cho tra loi huong dan gui feedback va giai thich dashboard public.
- [x] Khong cho chatbot guest truy cap ticket, feedback raw, alert noi bo, agent logs.
- [ ] Them rate limit rieng cho chatbot guest.
- [ ] Them canned responses cho cac cau hoi thuong gap de giam chi phi LLM.

## 20. Quan sat he thong va van hanh

- [ ] Them healthcheck endpoint cho backend: DB connection, model loaded, LLM configured, scheduler status.
- [ ] Them trang hoac log xem trang thai agent run gan nhat.
- [ ] Theo doi latency cua upload feedback, classification, ticket trigger va agent pipeline.
- [ ] Theo doi error rate theo module: frontend, backend, Supabase, LLM, scheduler.
- [ ] Them alert noi bo khi scheduler dung chay hoac agent loi lien tiep.
- [ ] Ghi ro runbook: khi Supabase loi, LLM loi, deploy loi, RLS chan nham thi xu ly ra sao.
- [ ] Them backup/restore plan cho Supabase database.
- [ ] Them data retention policy cho feedback, chat_messages va agent logs.

## 21. CI/CD va chat luong code

- [ ] Them GitHub Actions chay lint/test/build cho frontend.
- [ ] Them GitHub Actions chay test backend pipeline.
- [ ] Them check schema/migration Supabase neu co thay doi DB.
- [ ] Them pre-commit hoac script format cho TypeScript va Python.
- [ ] Them typecheck frontend va validation cho generated Supabase types.
- [ ] Them smoke test toi thieu sau deploy.
- [ ] Tach config dev/staging/prod de tranh dung nham key.
- [ ] Them convention commit/branch va yeu cau cap nhat `JOURNAL.md`/`WORKLOG.md` truoc PR.

## 22. Docker hoa moi truong phat trien

- [ ] Tao `Dockerfile` cho backend FastAPI/pipeline.
- [ ] Tao `Dockerfile` cho frontend React/TanStack Start.
- [ ] Tao `docker-compose.yml` de chay frontend, backend va Supabase/local services neu phu hop.
- [ ] Chuan hoa bien moi truong qua `.env.example` va `.env.docker.example`.
- [ ] Dam bao thanh vien moi chi can `docker compose up` la chay duoc app.
- [ ] Them volume/cache hop ly cho node_modules, Python venv/model files de dev nhanh hon.
- [ ] Them healthcheck cho container backend va frontend.
- [ ] Them script seed data demo khi chay Docker lan dau.
- [ ] Viet huong dan Docker trong `README.md`: cai Docker Desktop, copy env, start/stop/reset.
- [ ] Kiem tra Docker tren may thanh vien khac hoac moi truong sach de tranh loi phu thuoc local.

## 23. Quan tri to chuc va team

- [ ] Them mo hinh organization/team neu san pham co nhieu phong ban hoac nhieu cong ty dung chung.
- [ ] Gan user vao team/department va role cu the: owner, manager, staff, support, guest.
- [ ] Them man hinh moi thanh vien, khoa tai khoan, doi role va gan team.
- [ ] Them ownership ro rang cho ticket/task: assigned_team, assignee_id, reviewer_id.
- [ ] Them rule de manager chi xem du lieu cua team minh neu can.
- [ ] Them audit log cho thay doi role, team, permission va assignment.

## 24. Notification va tich hop ben ngoai

- [ ] Them notification trong app khi co ticket P4/P5, SLA sap tre hoac task moi duoc assign.
- [ ] Them email notification cho manager/truong phong khi co report quan trong.
- [ ] Can nhac tich hop Slack/Discord/Zalo OA neu team van hanh dung kenh do.
- [ ] Them webhook outbound khi ticket/task doi status de tich hop voi he thong khac.
- [ ] Them notification preferences theo user/team de tranh spam.
- [ ] Them digest hang ngay/hang tuan cho truong phong.

## 25. Danh gia chat luong model va agent

- [ ] Tao bo evaluation dataset co label dung cho topic, sentiment, severity va feedback score.
- [ ] Do metric classification: accuracy, precision/recall theo class, confusion matrix.
- [ ] Do metric ticket routing: ti le route dung team, ti le P5 ve Safety, ti le ticket trung.
- [ ] Do metric agent/report: tinh day du, dung schema, co action plan, khong hallucinate du lieu.
- [ ] Them regression test de model/rule/prompt moi khong lam giam chat luong.
- [ ] Luu correction cua staff de tao tap evaluation va cai thien model sau nay.
- [ ] Them dashboard noi bo theo doi model drift va cac nhan hay bi sua lai.

## 26. Data ingestion tu nguon thuc te

- [ ] Xac dinh nguon du lieu production: app review, form feedback, CS ticket, hotline transcript, social comment.
- [ ] Tao connector/importer rieng cho tung nguon du lieu.
- [ ] Chuan hoa mapping source fields ve schema feedback canonical.
- [ ] Them co che incremental sync de khong import trung.
- [ ] Them validation pipeline cho data thieu area/topic/timestamp/user identifier.
- [ ] Them trang xem upload/import batches va loi import.
- [ ] Them co che an danh/ma hoa du lieu nhay cam truoc khi agent xu ly.

## 27. Privacy, compliance va an toan du lieu

- [ ] Xac dinh truong nao la PII: email, so dien thoai, ten, bien so xe, dia chi, noi dung nhay cam.
- [ ] Mask/redact PII truoc khi dua vao LLM.
- [ ] Khong gui du lieu raw nhay cam sang LLM neu khong can thiet.
- [ ] Them data access policy theo role va muc do nhay cam.
- [ ] Them retention policy: du lieu nao giu bao lau, log nao xoa sau bao lau.
- [ ] Them export/delete data theo user neu can tuan thu yeu cau privacy.
- [ ] Kiem tra secret scanning de khong commit API key, service_role key, token.

## 28. Backup, migration va disaster recovery

- [ ] Thiet lap backup Supabase/Postgres dinh ky.
- [ ] Viet huong dan restore database tu backup.
- [ ] Them migration strategy: tao migration, review, apply staging, apply production.
- [ ] Them seed data rieng cho dev/demo/staging.
- [ ] Them checklist rollback khi deploy backend/frontend/DB loi.
- [ ] Kiem tra app van hoat dong o che do read-only hoac degraded mode khi agent worker loi.

## 29. Dua len URL public de moi nguoi truy cap

- [ ] Chon phuong an deploy frontend: Vercel/Netlify/Render static.
- [ ] Chon phuong an deploy backend pipeline/API: Railway/Render/Fly.io hoac Supabase Edge neu phu hop.
- [ ] Cau hinh Supabase remote project, Auth redirect URL va RLS cho moi truong production.
- [ ] Cau hinh environment variables tren hosting, khong dung `.env` local.
- [ ] Doi `VITE_BACKEND_API_URL` va Supabase URL/key sang endpoint production.
- [ ] Kiem tra CORS cho backend production.
- [ ] Kiem tra scheduler/worker agent chay tren moi truong deploy, khong phu thuoc may local.
- [ ] Tao URL public cho frontend de moi nguoi co the vao dung.
- [ ] Smoke test tren URL public: login guest, xem dashboard, upload feedback, agent/ticket chay dung.
- [ ] Cap nhat `README.md` voi link URL public va cach van hanh production.
