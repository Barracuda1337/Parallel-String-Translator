import re
from deep_translator import GoogleTranslator
import chardet
import os
import math
import json
from datetime import datetime, date
import multiprocessing
import shutil
import psutil
import time
from pathlib import Path

# Sabit değişkenler
DAILY_LIMIT = 200000  # Google Translate günlük karakter limiti
RATE_LIMIT_DELAY = 1  # İstekler arası bekleme süresi (saniye)
TEMP_DIR = "temp"  # Geçici dosyaların saklanacağı ana klasör
PARTS_DIR = os.path.join(TEMP_DIR, "parts")  # Parça dosyaları klasörü
PROGRESS_DIR = os.path.join(TEMP_DIR, "progress")  # İlerleme dosyaları klasörü
STATS_DIR = os.path.join(TEMP_DIR, "stats")  # İstatistik dosyaları klasörü

class TranslationStats:
    def __init__(self):
        self.stats_file = os.path.join(STATS_DIR, f"stats_{date.today()}.json")
        self._load_stats()

    def _load_stats(self):
        if os.path.exists(self.stats_file):
            with open(self.stats_file, 'r') as f:
                stats = json.load(f)
                self.chars_translated = stats.get('chars_translated', 0)
                self.last_request = stats.get('last_request', 0)
        else:
            self.chars_translated = 0
            self.last_request = 0
        
    def _save_stats(self):
        os.makedirs(STATS_DIR, exist_ok=True)
        with open(self.stats_file, 'w') as f:
            json.dump({
                'chars_translated': self.chars_translated,
                'last_request': self.last_request,
                'last_update': datetime.now().isoformat()
            }, f)

    def can_translate(self, text_length):
        # Günlük limit kontrolü
        if self.chars_translated + text_length > DAILY_LIMIT:
            return False
        
        # Rate limit kontrolü
        current_time = time.time()
        if current_time - self.last_request < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - (current_time - self.last_request))
        
        return True

    def update_stats(self, text_length):
        self.chars_translated += text_length
        self.last_request = time.time()
        self._save_stats()

    def get_remaining_limit(self):
        return DAILY_LIMIT - self.chars_translated

def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        return result['encoding']

def translate_with_retry(translator, text, stats, max_retries=3):
    if not text.strip():
        return text

    text_length = len(text)
    if not stats.can_translate(text_length):
        remaining = stats.get_remaining_limit()
        print(f"⚠️ Günlük limit aşılıyor! Kalan karakter: {remaining:,}")
        return text

    for attempt in range(max_retries):
        try:
            translated = translator.translate(text=text)
            stats.update_stats(text_length)
            return translated
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Çeviri başarısız: {str(e)}")
                return text
            print(f"Yeniden deneniyor... ({attempt + 1}/{max_retries})")
            time.sleep(RATE_LIMIT_DELAY * 2)

def save_progress(part_num, last_line, total_lines):
    progress_file = os.path.join(PROGRESS_DIR, f"progress_{part_num:03d}.json")
    os.makedirs(PROGRESS_DIR, exist_ok=True)
    with open(progress_file, 'w') as f:
        json.dump({
            'last_line': last_line,
            'total_lines': total_lines,
            'completed': last_line >= total_lines - 1,
            'timestamp': datetime.now().isoformat()
        }, f)

def load_progress(part_num):
    progress_file = os.path.join(PROGRESS_DIR, f"progress_{part_num:03d}.json")
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            return json.load(f)
    return None

def get_optimal_process_count():
    cpu_count = psutil.cpu_count(logical=False)
    available_memory = psutil.virtual_memory().available / (1024 * 1024 * 1024)
    max_processes_by_memory = int(available_memory / 0.5)
    optimal_count = min(cpu_count, max_processes_by_memory)
    return max(1, min(optimal_count, 16))  # En fazla 16 paralel işlem

def process_file(input_file, part_num, start_line, end_line, file_encoding):
    translator = GoogleTranslator(source='de', target='tr')
    stats = TranslationStats()
    output_file = os.path.join(PARTS_DIR, f"part_{part_num:03d}.str")
    
    try:
        # İlerleme kontrolü
        progress = load_progress(part_num)
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
            
        start_idx = len(translated_lines)
        total = len(lines_to_process)
        
        # Limit bilgisini göster
        remaining_limit = stats.get_remaining_limit()
        print(f"Parça {part_num} başlıyor. Kalan günlük limit: {remaining_limit:,} karakter")
        
        for i, line in enumerate(lines_to_process[start_idx:], start=start_idx):
            if i % 10 == 0:
                progress = (i/total*100)
                remaining_limit = stats.get_remaining_limit()
                print(f"Parça {part_num}: {progress:.1f}% tamamlandı (Kalan limit: {remaining_limit:,})")
                
            match = re.match(r'(\S+)\s+"(.+)"', line.strip())
            if match:
                key, value = match.groups()
                translated_text = translate_with_retry(translator, value, stats)
                translated_line = f'{key} "{translated_text}"\n'
            else:
                translated_line = line
                
            translated_lines.append(translated_line)
            
            # Her 10 satırda bir kaydet
            if (i + 1) % 10 == 0 or i == len(lines_to_process) - 1:
                os.makedirs(PARTS_DIR, exist_ok=True)
                with open(output_file, 'w', encoding=file_encoding) as f:
                    f.writelines(translated_lines)
                save_progress(part_num, i + 1, total)
        
        save_progress(part_num, total, total)
        return True
    except Exception as e:
        print(f"Hata Parça {part_num}: {str(e)}")
        return False

def combine_files(final_output, file_encoding):
    print("\nParçalar birleştiriliyor...")
    with open(final_output, 'w', encoding=file_encoding) as outfile:
        part_files = sorted([f for f in os.listdir(PARTS_DIR) if f.startswith('part_') and f.endswith('.str')])
        for part_file in part_files:
            with open(os.path.join(PARTS_DIR, part_file), 'r', encoding=file_encoding) as infile:
                outfile.write(infile.read())

def create_directory_structure():
    """Gerekli klasör yapısını oluştur"""
    for directory in [TEMP_DIR, PARTS_DIR, PROGRESS_DIR, STATS_DIR]:
        os.makedirs(directory, exist_ok=True)

def main():
    # Klasör yapısını oluştur
    create_directory_structure()
    
    # Ayarlar
    input_file = "strings_german.str"
    final_output = "translated_output_final.str"
    
    # Sistem kaynaklarına göre optimum işlem sayısını belirle
    max_processes = get_optimal_process_count()
    
    # Dosya kodlamasını tespit et
    file_encoding = detect_encoding(input_file)
    
    # Sistem bilgilerini göster
    print("\n📊 Sistem Bilgileri:")
    print(f"CPU Çekirdek Sayısı: {psutil.cpu_count(logical=False)} (Fiziksel)")
    print(f"Toplam Bellek: {psutil.virtual_memory().total / (1024**3):.1f} GB")
    print(f"Kullanılabilir Bellek: {psutil.virtual_memory().available / (1024**3):.1f} GB")
    print(f"Seçilen Paralel İşlem Sayısı: {max_processes}")
    
    # Günlük limit bilgisini göster
    stats = TranslationStats()
    remaining_limit = stats.get_remaining_limit()
    print(f"\n🔄 Çeviri Limitleri:")
    print(f"Günlük Toplam Limit: {DAILY_LIMIT:,} karakter")
    print(f"Kullanılan: {stats.chars_translated:,} karakter")
    print(f"Kalan: {remaining_limit:,} karakter")
    
    # Toplam satır sayısını bul
    with open(input_file, 'r', encoding=file_encoding) as f:
        total_lines = sum(1 for _ in f)
    
    # Her parçada olacak satır sayısını hesapla
    lines_per_part = math.ceil(total_lines / 100)  # 100 parça
    num_parts = math.ceil(total_lines / lines_per_part)
    
    print(f"\n📝 Çeviri Bilgileri:")
    print(f"Dosya Kodlaması: {file_encoding}")
    print(f"Toplam {total_lines:,} satır")
    print(f"Her parça yaklaşık {lines_per_part:,} satır içerecek")
    print(f"Toplam {num_parts} parça oluşturulacak")
    
    # Parçaları hazırla
    tasks = []
    for i in range(num_parts):
        start_line = i * lines_per_part
        end_line = min((i + 1) * lines_per_part, total_lines)
        tasks.append((input_file, i, start_line, end_line, file_encoding))
    
    # Paralel işleme başlat
    start_time = datetime.now()
    print("\n🚀 Çeviri başlıyor...")
    
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
    combine_files(final_output, file_encoding)
    
    # İsteğe bağlı temizlik
    clean = input("\n🗑️ Geçici dosyalar silinsin mi? (E/H): ").lower()
    if clean == 'e':
        shutil.rmtree(TEMP_DIR)
        print("Geçici dosyalar temizlendi.")
    else:
        print(f"Geçici dosyalar '{TEMP_DIR}' klasöründe saklandı.")
    
    # Son istatistikleri göster
    total_duration = (datetime.now() - start_time).total_seconds()
    stats = TranslationStats()
    print(f"\n✨ İşlem tamamlandı!")
    print(f"Toplam süre: {total_duration/60:.1f} dakika")
    print(f"Ortalama hız: {total_lines/total_duration:.1f} satır/saniye")
    print(f"Çevrilen karakter: {stats.chars_translated:,}")
    print(f"Kalan günlük limit: {stats.get_remaining_limit():,}")
    print(f"Sonuç dosyası: {final_output}")

if __name__ == '__main__':
    main() 
