import re
from deep_translator import GoogleTranslator
import chardet
import os
import math
import json
from datetime import datetime
import multiprocessing
import shutil

def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        return result['encoding']

def translate_with_retry(translator, text, max_retries=3):
    for attempt in range(max_retries):
        try:
            return translator.translate(text=text)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Çeviri başarısız: {str(e)}")
                return text
            print(f"Yeniden deneniyor...")

def save_progress(output_dir, part_num, last_line, total_lines):
    progress_file = os.path.join(output_dir, f"progress_{part_num:03d}.json")
    with open(progress_file, 'w') as f:
        json.dump({
            'last_line': last_line,
            'total_lines': total_lines,
            'completed': last_line >= total_lines - 1
        }, f)

def load_progress(output_dir, part_num):
    progress_file = os.path.join(output_dir, f"progress_{part_num:03d}.json")
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            return json.load(f)
    return None

def process_file(input_file, output_file, start_line, end_line, part_num, file_encoding, output_dir):
    translator = GoogleTranslator(source='de', target='tr')
    
    try:
        # İlerleme kontrolü
        progress = load_progress(output_dir, part_num)
        if progress and progress['completed']:
            print(f"Parça {part_num} zaten tamamlanmış, atlanıyor...")
            return True

        # Mevcut çevrilmiş satırları yükle
        translated_lines = []
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding=file_encoding) as f:
                translated_lines = f.readlines()

        with open(input_file, 'r', encoding=file_encoding) as f:
            all_lines = f.readlines()
            lines_to_process = all_lines[start_line:end_line]
            
        start_idx = len(translated_lines)  # Kaldığı yerden devam et
        total = len(lines_to_process)
        
        for i, line in enumerate(lines_to_process[start_idx:], start=start_idx):
            if i % 10 == 0:
                print(f"Parça {part_num}: {(i/total*100):.1f}% tamamlandı")
                
            match = re.match(r'(\S+)\s+"(.+)"', line.strip())
            if match:
                key, value = match.groups()
                translated_text = translate_with_retry(translator, value)
                translated_line = f'{key} "{translated_text}"\n'
            else:
                translated_line = line
                
            translated_lines.append(translated_line)
            
            # Her 10 satırda bir kaydet ve ilerlemeyi güncelle
            if (i + 1) % 10 == 0 or i == len(lines_to_process) - 1:
                with open(output_file, 'w', encoding=file_encoding) as f:
                    f.writelines(translated_lines)
                save_progress(output_dir, part_num, i + 1, total)
        
        # Son durumu kaydet
        save_progress(output_dir, part_num, total, total)
        return True
    except Exception as e:
        print(f"Hata Parça {part_num}: {str(e)}")
        return False

def combine_files(output_dir, final_output, file_encoding):
    with open(final_output, 'w', encoding=file_encoding) as outfile:
        part_files = sorted([f for f in os.listdir(output_dir) if f.startswith('part_') and f.endswith('.str')])
        for part_file in part_files:
            with open(os.path.join(output_dir, part_file), 'r', encoding=file_encoding) as infile:
                outfile.write(infile.read())

def main():
    # Ayarlar
    input_file = "strings_german.str"
    output_dir = "translation_parts"
    final_output = "translated_output_final.str"
    max_processes = 50  # Aynı anda işlenecek parça sayısını 16'ya çıkardım
    
    # Çıktı klasörünü oluştur (varsa korur)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Dosya kodlamasını tespit et
    file_encoding = detect_encoding(input_file)
    print(f"Tespit edilen dosya kodlaması: {file_encoding}")
    
    # Toplam satır sayısını bul
    with open(input_file, 'r', encoding=file_encoding) as f:
        total_lines = sum(1 for _ in f)
    
    # Her parçada olacak satır sayısını hesapla
    lines_per_part = math.ceil(total_lines / 100)  # 100 parça
    num_parts = math.ceil(total_lines / lines_per_part)
    
    print(f"Toplam {total_lines} satır")
    print(f"Her parça yaklaşık {lines_per_part} satır içerecek")
    print(f"Toplam {num_parts} parça oluşturulacak")
    print(f"Aynı anda {max_processes} parça işlenecek")
    
    # Parçaları hazırla
    tasks = []
    for i in range(num_parts):
        start_line = i * lines_per_part
        end_line = min((i + 1) * lines_per_part, total_lines)
        output_file = os.path.join(output_dir, f"part_{i:03d}.str")
        tasks.append((input_file, output_file, start_line, end_line, i, file_encoding, output_dir))
    
    # Paralel işleme başlat
    start_time = datetime.now()
    print("\nÇeviri başlıyor...")
    
    with multiprocessing.Pool(max_processes) as pool:
        results = []
        for i, task in enumerate(tasks):
            result = pool.apply_async(process_file, task)
            results.append(result)
            
            # Her max_processes kadar görev başlatıldığında veya son görevde bekle
            if (i + 1) % max_processes == 0 or i == len(tasks) - 1:
                for r in results:
                    r.wait()
                results = []
    
    # Sonuçları birleştir
    print("\nParçalar birleştiriliyor...")
    combine_files(output_dir, final_output, file_encoding)
    
    # İsteğe bağlı temizlik
    clean = input("\nGeçici dosyalar silinsin mi? (E/H): ").lower()
    if clean == 'e':
        shutil.rmtree(output_dir)
        print("Geçici dosyalar temizlendi.")
    else:
        print(f"Geçici dosyalar '{output_dir}' klasöründe saklandı.")
    
    total_duration = (datetime.now() - start_time).total_seconds()
    print(f"\n✨ İşlem tamamlandı!")
    print(f"Toplam süre: {total_duration/60:.1f} dakika")
    print(f"Sonuç dosyası: {final_output}")

if __name__ == '__main__':
    main()
