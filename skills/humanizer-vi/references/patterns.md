# Nhóm pattern của humanizer-vi

Catalog máy đọc nằm trong `patterns/humanizer.yml`: 27 pattern chia bốn nhóm. File này là bản đồ để tra nhanh, không lặp lại chi tiết của yml.

## Lexical (9)

VI-HUM-L01 dong-vai-tro-trong-viec · VI-HUM-L02 boi-canh-khong-ngung-phat-trien · VI-HUM-L03 loi-khen-chung-chung · VI-HUM-L04 thanh-ngu-dich-sat · VI-HUM-L05 tinh-tu-rong · VI-HUM-L06 han-viet-lech-register · VI-HUM-L07 lap-tu-khong-doi-dong-nghia · VI-HUM-L08 mo-bai-thoi-dai-ngay-nay · VI-HUM-L09 chi-dinh-calque-day-dac

Cụm trừu tượng dài, lời khẳng định rỗng, giọng quảng cáo không có căn cứ, thành ngữ dịch sát, vốn từ bó hẹp và từ Hán-Việt lệch register.

## Discourse (7)

VI-HUM-D01 mo-bai-thong-bao-noi-dung · VI-HUM-D02 ket-bai-xa-giao · VI-HUM-D03 dan-nguon-mo-ho · VI-HUM-D04 meta-dan-duong · VI-HUM-D05 mo-dau-lich-su-thai-qua · VI-HUM-D06 ket-huong-toi-tuong-lai-mo-ho · VI-HUM-D07 tom-tat-thua-tung-muc

Mở bài thông báo, kết luận xã giao, dẫn nguồn mơ hồ, nhãn điều hướng giữa thân bài và phần kết không thêm thông tin nào.

## Structural (7)

VI-HUM-S01 lap-cau-mo-dau-bang-viec · VI-HUM-S02 khong-chi-ma-con-lap · VI-HUM-S03 tu-noi-day-dac · VI-HUM-S04 do-dai-cau-dong-deu · VI-HUM-S05 doan-dai-dong-deu · VI-HUM-S06 markdown-qua-lieu · VI-HUM-S07 chuoi-danh-hoa-viec-su

Nhiều câu cùng mở đầu, nhịp câu và nhịp đoạn quá đều, từ nối dày, trình bày quá liều và chuỗi danh hóa che động từ chính.

## Pragmatic (4)

VI-HUM-P01 xung-ho-khong-nhat-quan · VI-HUM-P02 ban-mac-dinh-calque-you · VI-HUM-P03 thieu-tinh-thai-tu · VI-HUM-P04 thanh-ngu-vang-hoac-sai

Nhóm này lần đầu có pattern thật. Đây là tín hiệu đặc thù tiếng Việt — hệ xưng hô, tình thái từ, thành ngữ bản địa — chứ không phải lỗi từ vựng.

## Cách đọc catalog

Pattern là gợi ý review, không phải danh sách từ cấm. `confidence: low` là lời nhắc đọc lại câu đó, không bao giờ tự nó là lý do sửa. Cần một tín hiệu thứ hai — mất thông tin, sai register, hoặc người đọc thật sự vấp — trước khi đụng vào văn bản. Nhóm tin cậy thấp: L04, L05, L06, L09, S04, S05, S06, D07, P02, P03, P04.

`false_positive_risk: high` chỉ áp dụng trong đúng những register mà trường `exceptions` của chính pattern đó nêu tên. Ngoài các register ấy, ghi nhận rồi bỏ qua. Nhóm rủi ro cao: L06, L09, S02, S04, S05, S06, P02, P03, P04.

## Quy tắc áp dụng

Chỉ sửa `VI-HUM-L01` khi cấu trúc "đóng vai trò... trong việc" che mất hành động. `VI-HUM-S04` về độ dài câu và `VI-HUM-S05` về độ dài đoạn chỉ có độ tin cậy thấp. Trong văn bản hành chính hay học thuật, cấu trúc đều và danh hóa có thể hợp lệ.

Lời dẫn "trong bối cảnh ... phát triển" có thể đủ để tạo một finding khi chính câu đó không nêu thay đổi cụ thể. Không ghép "trong bối cảnh" ở một câu với "không ngừng phát triển" ở câu sau.

Pattern nhóm Pragmatic bị khóa theo register. Tra `references/registers.md` trước khi áp bất kỳ pattern nào từ P01 đến P04, và không áp chúng cho văn bản hành chính, pháp lý, học thuật hay kỹ thuật.

`VI-HUM-L09` và `VI-HUM-S07` giáp ranh với `translationese-cleaner-vi`. Hai pattern này chỉ đánh dấu mật độ rồi định tuyến; phần sửa sâu trật tự câu theo tiếng Anh, "của" và "được" thừa cùng cấu trúc calque thuộc skill kia, không thuộc skill này.

Khi hai pattern cùng đánh vào một câu, sửa một lần ở cấp cấu trúc rồi đánh giá lại. Không thay lần lượt từng cụm vì dễ tạo văn bản vá víu.
