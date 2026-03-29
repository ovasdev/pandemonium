#!/usr/bin/env bash
# Квантовая кость — квантовые случайные числа в заданном диапазоне.
# Источники: LfD QRNG (основной), ANU QRNG (фолбэк).
# Использование: ./quantum_random.sh <количество> [from] [to]
#   количество — сколько чисел сгенерировать (>= 1)
#   from       — нижняя граница диапазона (по умолчанию 0)
#   to         — верхняя граница диапазона (по умолчанию 255)

set -euo pipefail

LFD_API="https://lfdr.de/qrng_api/qrng"
ANU_API="https://qrng.anu.edu.au/API/jsonI.php"
ANU_MAX=1024

count="${1:-}"
from="${2:-0}"
to="${3:-255}"

if [[ -z "$count" ]] || ! [[ "$count" =~ ^[0-9]+$ ]] || (( count < 1 )); then
  echo "Использование: $0 <количество> [from] [to]" >&2
  echo "  количество — сколько случайных чисел получить (>= 1)" >&2
  echo "  from       — нижняя граница (по умолчанию 0)" >&2
  echo "  to         — верхняя граница (по умолчанию 255)" >&2
  exit 1
fi

if ! [[ "$from" =~ ^[0-9]+$ ]] || ! [[ "$to" =~ ^[0-9]+$ ]] || (( from >= to )); then
  echo "Ошибка: from ($from) должен быть меньше to ($to), оба >= 0" >&2
  exit 1
fi

range=$(( to - from + 1 ))

# --- LfD QRNG: возвращает hex-строку, парсим в числа ---
fetch_lfd() {
  local n=$1
  local response
  response=$(curl -sf --connect-timeout 5 "${LFD_API}?length=${n}&format=HEX") || return 1
  local hex
  hex=$(echo "$response" | jq -r '.qrn // empty') || return 1
  [[ -z "$hex" ]] && return 1
  echo "$hex" | fold -w2 | while read -r byte; do
    printf '%d\n' "0x${byte}"
  done
}

# --- ANU QRNG: возвращает JSON-массив uint8 ---
fetch_anu() {
  local n=$1
  local result=""
  local remaining=$n

  while (( remaining > 0 )); do
    local batch=$(( remaining > ANU_MAX ? ANU_MAX : remaining ))
    local response
    response=$(curl -sf --connect-timeout 5 "${ANU_API}?length=${batch}&type=uint8") || return 1
    local success
    success=$(echo "$response" | jq -r '.success') || return 1
    [[ "$success" != "true" ]] && return 1
    local batch_data
    batch_data=$(echo "$response" | jq -r '.data | map(tostring) | join("\n")') || return 1

    if [[ -n "$result" ]]; then
      result="${result}"$'\n'"${batch_data}"
    else
      result="$batch_data"
    fi
    remaining=$(( remaining - batch ))
  done

  echo "$result"
}

# --- Порог для rejection sampling ---
# Отбрасываем байты >= threshold, чтобы каждое значение в диапазоне
# было строго равновероятным. Для range=256 (полный диапазон) ничего не отбрасываем.
threshold=$(( 256 - (256 % range) ))

fetch_raw() {
  local n=$1
  fetch_lfd "$n" 2>/dev/null || fetch_anu "$n" 2>/dev/null || {
    echo "Ошибка: квантовая кость недоступна — ни один QRNG API не отвечает" >&2
    exit 1
  }
}

# --- Rejection sampling: собираем ровно $count равномерных чисел ---
collected=0
# Запрашиваем с запасом ~20% на отброшенные байты
batch_size=$(( count + count / 5 + 10 ))

while (( collected < count )); do
  raw=$(fetch_raw "$batch_size")
  while IFS= read -r n; do
    (( n >= threshold )) && continue
    echo $(( from + (n % range) ))
    collected=$(( collected + 1 ))
    (( collected >= count )) && break
  done <<< "$raw"
done
