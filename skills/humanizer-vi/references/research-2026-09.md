# Tóm tắt nghiên cứu — 2026-09

Ngày khảo sát: 2026-09-04. Phương pháp: NotebookLM deep web research, prompt song ngữ Việt–Anh, 59 nguồn, kèm một báo cáo tổng hợp do NotebookLM sinh ra.

Bản đầy đủ: `~/.claude/projects/system-improvement/outputs/notebooklm-research/2026-09-04-spot-ai-writing-vi/`.
Mã nguồn tám ký tự trong ngoặc vuông tra được ở `sources.md` của thư mục đó.

Đây là tài liệu tham khảo cho việc biên tập, không phải hướng dẫn phát hiện. Mọi mục dưới đây là gợi ý để đọc lại một đoạn văn, không phải bằng chứng về tác giả. Một tín hiệu đơn lẻ không kết luận được gì.

## Từ vựng — độ tin cậy thấp

Cụm sáo rỗng dịch thẳng từ thành ngữ tiếng Anh: "bước tiến đúng hướng", "một phần nhỏ của tảng băng chìm" [9b106d82]. Mở bài công thức: "trong thế giới nhịp sống nhanh ngày nay", "khi chúng ta đối mặt với sự phức tạp", "tôi hy vọng bạn vẫn khỏe khi nhận được email này" [eefd573e]. Kết bài mở ra tương lai mơ hồ kiểu "khi trí tuệ nhân tạo tiếp tục phát triển" [eefd573e].

Tính từ khen rỗng, không kèm số liệu: "mạnh mẽ", "liền mạch", "sống động", "mang tính đột phá", "then chốt", "mang tính chuyển đổi" [eefd573e].

Hán-Việt trang trọng đặt vào ngữ cảnh đời thường: "lĩnh vực", "tận dụng", "khai thác", "đào sâu". Nguồn gốc được quy cho RLHF: người dán nhãn chấm điểm cao cho văn nghe cầu kỳ [eefd573e].

Calque từ tiếng Anh: "điều này", "việc này", "nơi", "bởi" lặp bất thường do bám sát this/that/these/by [9b106d82]. Lặp một từ với tần suất cao trong đoạn ngắn, ví dụ "hỗ trợ" ba lần trong ba câu liền [9b106d82].

## Cấu trúc và diễn ngôn

Nhịp câu đều. Các câu dài xấp xỉ nhau, không có câu cực ngắn để nhấn, không có câu dài biến tấu [a5bb48c4].

Đối xứng đoạn bắt buộc. Bố cục năm đoạn: mở bài chung, ba đoạn thân bài dài bằng nhau, kết bài hướng tương lai [eefd573e].

Tóm tắt thừa chèn ở cuối mỗi mục nhỏ, ngoài dàn ý được yêu cầu [eefd573e].

Cấu trúc song song và bộ ba: "không chỉ X mà còn Y" dùng với tần suất rất cao; chuỗi câu ngắn lặp cùng khuôn ngữ pháp [eefd573e, 9b106d82].

Meta-narration: "trong phần này chúng ta sẽ", "như đã đề cập ở trên", "bây giờ chúng ta đã thảo luận về X, hãy cùng xem xét Y" [eefd573e].

Rào đón và lịch sự thái quá, đặc biệt trong email [eefd573e].

Dấu câu và định dạng: lạm dụng gạch ngang dài, hai chấm dẫn nhập cho mọi danh sách, in đậm dày đặc và bullet nhiều tầng [eefd573e, 9b106d82]. Sạch lỗi chính tả và dấu câu một cách tuyệt đối cũng được liệt kê như một chỉ dấu [9b106d82].

Bị động che chủ thể và danh hóa rườm rà: "việc", "sự", "một cách" thêm vào để dịch các hậu tố -ing, -tion, -ly [9b106d82, eefd573e]. Translationese: thừa "của", nối câu dài bằng "và", trật tự từ bám ngữ pháp tiếng Anh [6836dff1].

## Đặc thù tiếng Việt

Xưng hô. Lạm dụng "bạn" như bản dịch mặc định của "you"; trộn lẫn tôi, chúng ta, bạn, quý vị trong cùng một văn bản; xã giao thừa kiểu dịch máy ở đầu email [eefd573e, 77a0c856].

Tình thái từ. Thiếu hẳn các trợ từ cuối câu tự nhiên: nhé, nhỉ, à, ạ, thôi, mà. Văn bản vì thế nghe vô trùng ở các ngữ cảnh lẽ ra phải mềm [77a0c856, eefd573e].

Thành ngữ. Ít dùng thành ngữ thuần Việt đúng chỗ, thay vào đó là thành ngữ tiếng Anh dịch thô [9b106d82].

Trộn từ vựng Bắc/Nam: bộ nguồn không có tài liệu nào bàn về hiện tượng này. Không suy diễn thêm.

## Fingerprint theo mô hình

ChatGPT: bố cục bài luận năm đoạn, từ nối rập khuôn (hơn nữa, tóm lại), câu điều hướng vô nghĩa, ưa từ Hán-Việt dịch từ tiếng Anh học thuật [eefd573e].

Gemini: mạnh về thị giác và OCR tiếng Việt, nhưng khi đơn giản hóa tài liệu phức tạp hay sinh khối văn bản lớn, thiếu phân đoạn rõ [636c41ea, b58c8dd7].

Claude: hành văn học thuật và lập luận được đánh giá cao, nhưng ở tác vụ đơn giản hóa văn bản luật, điểm danh nghĩa cao lại che các lỗi lập luận tinh vi như ví dụ sai và hiểu sai ngữ cảnh [b58c8dd7].

DeepSeek-V3: văn phong tự nhiên hơn, vượt được hầu hết máy dò thống kê phổ biến trong thử nghiệm Capybara [c4147849].

PhoGPT (VinAI): 4 tỷ tham số, huấn luyện trên 102 tỷ token tiếng Việt, tokenizer riêng. PhoGPT-4B và PhoGPT-4B-Chat được chọn làm cặp observer/performer cho các detector tiếng Việt [c4147849, 69d49444].

Fingerprint là phần dễ lỗi thời nhất trong tài liệu này. Đọc như bối cảnh, không dùng để gán mô hình cho một đoạn văn.

## Số liệu detector

VietBinoculars: tỉ số perplexity trên cross-perplexity với cặp PhoGPT-4B. Trên tập validation tin tức đạt khoảng 96% ở ngưỡng Youden's J 0.86; trên dữ liệu out-of-domain do Gemma-3-12B và Sailor2-8B sinh, F1 và accuracy 99–100% [c4147849].

VietAIDetector: cùng thuật toán, thêm cửa sổ trượt cho tài liệu dài. Trong thử nghiệm tháng 7/2026 trên văn bản dài, điểm AI trung bình 96–100% tùy mô hình sinh, so với GPTZero ở mức 70–82% [98907b8b, 69d49444].

Thử nghiệm Capybara, tức người dùng cố tình nhét từ khóa dị thường để đẩy perplexity: VietBinoculars (Closest Point) 80.95%, VietBinoculars (Youden's J) 71.43%, Ghostbuster 33.33%, GPTZero và DetectGPT 14.29%, RadarTester 4.76%; Turnitin không hỗ trợ tiếng Việt [c4147849].

ViDetect, 6.800 bài luận học sinh: mô hình giám sát tốt nhất đạt 89.57% ở 64 token; AUROC trung bình tăng từ 0.8629 (64 token) lên 0.9168 (256 token) [15d9accb, b2d79ac1]. Đoạn dưới 50 token quá nghèo đặc trưng thống kê để đo [c4147849].

Ngưỡng an toàn học thuật của VietBinoculars đặt ở 0.70, chấp nhận giảm độ nhạy để giữ báo động giả quanh 6 trên 10.000 bài người thật [c4147849]. Chính người xây công cụ cũng coi dương tính giả là chi phí phải trả.

## Dương tính giả

Cơ chế: detector chấm perplexity. Từ ngữ càng dễ đoán, điểm càng nghiêng về AI [a5bb48c4].

Văn bản hành chính, pháp lý, học thuật và báo chí chính thống bắt buộc dùng thuật ngữ cố định, cụm chuyển ý chuẩn và cú pháp quy phạm, nên perplexity thấp tự nhiên và bị gắn cờ oan [00e478a7, a5bb48c4]. Đây là lý do hai mục bảo toàn mới trong `preservation-rules.md` tồn tại.

Định kiến với người viết không phải bản ngữ: nghiên cứu Stanford (Weixin Liang, 2023) ghi nhận 61% bài luận TOEFL do người viết bị gắn cờ nhầm là AI [a5bb48c4, 77a0c856].

Turnitin ẩn điểm dưới 20%, khuyến cáo không dùng điểm làm bằng chứng duy nhất; nhiều đại học đã tắt tính năng [a5bb48c4].

Kết luận trong bộ nguồn: không detector nào đáng tin 100%; điểm số chỉ là tham khảo, không phải phán quyết [da423313, 77a0c856].

## Độ tin cậy của chính tài liệu này

Phần từ vựng: THẤP. Nó chỉ dựa trên hai nguồn web là tex.vn [9b106d82] và bản dịch của VnReview cho một bài Towards AI [eefd573e]. Phần lớn mục trong đó là tell tiếng Anh được dịch sang tiếng Việt (delve thành "đào sâu", seamless thành "liền mạch"), không phải tần suất đo trên ngữ liệu tiếng Việt. Dùng như gợi ý để đọc lại, không bao giờ như danh sách từ cấm.

Phần cấu trúc và diễn ngôn: khá hơn, nhưng vẫn chủ yếu là quan sát nghề nghiệp, không phải thống kê ngữ liệu.

Phần số liệu detector: CAO. Nguồn là ba bài arXiv — 2405.03206, 2509.26189 (VietBinoculars), 2608.25478 (VietAIDetector).

Phần Turnitin và nghiên cứu Stanford: chỉ truy được đến trang giới thiệu công cụ thương mại trong bộ nguồn, chưa về tới bài gốc. Dùng như tham khảo, không dẫn như số liệu chắc.

Bộ nguồn còn chứa một nhóm bài về lỗi phông chữ tiếng Việt khi tạo ảnh AI. Đó là chuyện sinh ảnh, không liên quan đến biên tập văn bản, và đã được loại khỏi tóm tắt này.

## Hạn dùng

Tell thay đổi theo mô hình. Danh mục ở đây là ảnh chụp tháng 9/2026: nó phản ánh thói quen của các mô hình đang phổ biến tại thời điểm đó, và những thói quen ấy đã được đưa vào prompt chống AI khắp nơi, nên chính chúng sẽ bị huấn luyện mất dần. Đọc lại và soát lại danh mục này trước khi dùng, đừng tin nó vô thời hạn. Khi một mục không còn đúng, sửa mục đó thay vì giữ để cho đủ.
