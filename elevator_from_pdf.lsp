;; АВТОМАТИЧНО ЗГЕНЕРОВАНА СХЕМА З PDF
;; Джерело: Технологія 06.06.24.pdf (сторінка 1)
;; Генератор: AI Agent
;; Завантаження: (load "D:/autocad project/elevator_from_pdf.lsp")
;; Запуск: (c:drawfullscheme)

(defun c:drawfullscheme ()
  (setvar "CMDECHO" 0)

  (princ "\n🌾 Генерую ПОВНУ схему з PDF...\n")

  ;; ========================================
  ;; СТВОРЕННЯ ШАРІВ
  ;; ========================================
  (princ "\n📐 Створюю шари...\n")

  (command "._LAYER" "N" "EQUIPMENT" "C" "5" "EQUIPMENT" "")
  (command "._LAYER" "N" "FLOW" "C" "1" "FLOW" "")
  (command "._LAYER" "N" "AIR" "C" "4" "AIR" "")
  (command "._LAYER" "N" "TEXT" "C" "7" "TEXT" "")
  (command "._LAYER" "N" "VALVES" "C" "3" "VALVES" "")

  ;; ========================================
  ;; СИЛОСИ (6 штук, 2 ряди)
  ;; ========================================
  (princ "\n🏗️  Малюю силоси...\n")
  (command "._LAYER" "S" "EQUIPMENT" "")

  ;; Силос 1
  (command "._CIRCLE" (list 20 70) 11.0)
  (command "._CIRCLE" (list 20 70) 10.5)
  (command "._LINE" (list 9.0 60) (list 9.0 70) "")
  (command "._LINE" (list 31.0 60) (list 31.0 70) "")
  (command "._LINE" (list 9.0 60) (list 20 56) "")
  (command "._LINE" (list 31.0 60) (list 20 56) "")
  (command "._TEXT" (list 18 70) 3 0 "1")
  (command "._TEXT" (list 15 80) 0.6 0 "MCBY 220.13.B12")

  ;; Силос 2
  (command "._CIRCLE" (list 45 70) 11.0)
  (command "._CIRCLE" (list 45 70) 10.5)
  (command "._LINE" (list 34.0 60) (list 34.0 70) "")
  (command "._LINE" (list 56.0 60) (list 56.0 70) "")
  (command "._LINE" (list 34.0 60) (list 45 56) "")
  (command "._LINE" (list 56.0 60) (list 45 56) "")
  (command "._TEXT" (list 43 70) 3 0 "2")
  (command "._TEXT" (list 40 80) 0.6 0 "MCBY 220.13.B12")

  ;; Силос 3
  (command "._CIRCLE" (list 20 40) 11.0)
  (command "._CIRCLE" (list 20 40) 10.5)
  (command "._LINE" (list 9.0 30) (list 9.0 40) "")
  (command "._LINE" (list 31.0 30) (list 31.0 40) "")
  (command "._LINE" (list 9.0 30) (list 20 26) "")
  (command "._LINE" (list 31.0 30) (list 20 26) "")
  (command "._TEXT" (list 18 40) 3 0 "3")
  (command "._TEXT" (list 15 50) 0.6 0 "MCBY 220.13.B12")

  ;; Силос 4
  (command "._CIRCLE" (list 45 40) 11.0)
  (command "._CIRCLE" (list 45 40) 10.5)
  (command "._LINE" (list 34.0 30) (list 34.0 40) "")
  (command "._LINE" (list 56.0 30) (list 56.0 40) "")
  (command "._LINE" (list 34.0 30) (list 45 26) "")
  (command "._LINE" (list 56.0 30) (list 45 26) "")
  (command "._TEXT" (list 43 40) 3 0 "4")
  (command "._TEXT" (list 40 50) 0.6 0 "MCBY 220.13.B12")

  ;; Силос 5
  (command "._CIRCLE" (list 85 55) 11.0)
  (command "._CIRCLE" (list 85 55) 10.5)
  (command "._LINE" (list 74.0 45) (list 74.0 55) "")
  (command "._LINE" (list 96.0 45) (list 96.0 55) "")
  (command "._LINE" (list 74.0 45) (list 85 41) "")
  (command "._LINE" (list 96.0 45) (list 85 41) "")
  (command "._TEXT" (list 83 55) 3 0 "5")
  (command "._TEXT" (list 80 65) 0.6 0 "MCBY 220.13.B12")

  ;; Силос 6
  (command "._CIRCLE" (list 110 55) 11.0)
  (command "._CIRCLE" (list 110 55) 10.5)
  (command "._LINE" (list 99.0 45) (list 99.0 55) "")
  (command "._LINE" (list 121.0 45) (list 121.0 55) "")
  (command "._LINE" (list 99.0 45) (list 110 41) "")
  (command "._LINE" (list 121.0 45) (list 110 41) "")
  (command "._TEXT" (list 108 55) 3 0 "6")
  (command "._TEXT" (list 105 65) 0.6 0 "MCBY 220.13.B12")

  ;; ========================================
  ;; БУНКЕРИ ПРИЙОМУ
  ;; ========================================
  (princ "\n📦 Малюю бункери...\n")

  ;; Бункер H1
  (command "._LINE" (list 10 93) (list 16 93) "")
  (command "._LINE" (list 16 93) (list 15 89) "")
  (command "._LINE" (list 15 89) (list 11 89) "")
  (command "._LINE" (list 11 89) (list 10 93) "")
  (command "._TEXT" (list 11 94) 1.2 0 "H1")
  (command "._TEXT" (list 10 91) 0.7 0 "100 т/год")

  ;; Бункер H3
  (command "._LINE" (list 30 93) (list 36 93) "")
  (command "._LINE" (list 36 93) (list 35 89) "")
  (command "._LINE" (list 35 89) (list 31 89) "")
  (command "._LINE" (list 31 89) (list 30 93) "")
  (command "._TEXT" (list 31 94) 1.2 0 "H3")
  (command "._TEXT" (list 30 91) 0.7 0 "100 т/год")

  ;; Бункер H4
  (command "._LINE" (list 50 93) (list 56 93) "")
  (command "._LINE" (list 56 93) (list 55 89) "")
  (command "._LINE" (list 55 89) (list 51 89) "")
  (command "._LINE" (list 51 89) (list 50 93) "")
  (command "._TEXT" (list 51 94) 1.2 0 "H4")
  (command "._TEXT" (list 50 91) 0.7 0 "100 т/год")

  ;; ========================================
  ;; НОРІЇ
  ;; ========================================
  (princ "\n⬆️  Малюю норії...\n")

  ;; Норія H5
  (command "._RECTANG" (list 72 10) (list 76 60))
  (command "._CIRCLE" (list 74 62) 1.5)
  (command "._TEXT" (list 73 35.0) 1.5 0 "H5")
  (command "._TEXT" (list 72 32.0) 0.7 0 "100 т/год")

  ;; Норія H6
  (command "._RECTANG" (list 100 10) (list 104 75))
  (command "._CIRCLE" (list 102 77) 1.5)
  (command "._TEXT" (list 101 42.5) 1.5 0 "H6")
  (command "._TEXT" (list 100 39.5) 0.7 0 "100 т/год")

  ;; ========================================
  ;; ТРАНСПОРТЕРИ (червоні лінії зі стрілками)
  ;; ========================================
  (princ "\n🔗 Малюю транспортери...\n")
  (command "._LAYER" "S" "FLOW" "")

  ;; T7
  (command "._LINE" (list 30 82) (list 72 65) "")
  (command "._TEXT" (list 51.0 74.5) 0.8 0 "T7")

  ;; T8
  (command "._LINE" (list 72 65) (list 20 68) "")
  (command "._TEXT" (list 46.0 67.5) 0.8 0 "T8")

  ;; T9
  (command "._LINE" (list 20 52) (list 72 8) "")
  (command "._TEXT" (list 46.0 31.0) 0.8 0 "T9")

  ;; T10
  (command "._LINE" (list 100 75) (list 45 68) "")
  (command "._TEXT" (list 72.5 72.5) 0.8 0 "T10")

  ;; T11
  (command "._LINE" (list 100 75) (list 85 53) "")
  (command "._TEXT" (list 92.5 65.0) 0.8 0 "T11")

  ;; T12
  (command "._LINE" (list 45 22) (list 100 8) "")
  (command "._TEXT" (list 72.5 16.0) 0.8 0 "T12")

  ;; T13
  (command "._LINE" (list 20 22) (list 45 22) "")
  (command "._TEXT" (list 32.5 23.0) 0.8 0 "T13")

  ;; T14
  (command "._LINE" (list 100 75) (list 110 53) "")
  (command "._TEXT" (list 105.0 65.0) 0.8 0 "T14")

  ;; T15
  (command "._LINE" (list 85 37) (list 110 37) "")
  (command "._TEXT" (list 97.5 38.0) 0.8 0 "T15")

  ;; T16
  (command "._LINE" (list 85 37) (list 100 8) "")
  (command "._TEXT" (list 92.5 23.5) 0.8 0 "T16")

  ;; ========================================
  ;; ЗАГОЛОВОК ТА ФІНІШ
  ;; ========================================
  (command "._LAYER" "S" "TEXT" "")
  (command "._TEXT" (list 40 95) 2 0 "Схема технологічного процесу")
  (command "._TEXT" (list 110 2) 0.8 0 "05. 06. 2024")

  (command "._ZOOM" "_E")

  (princ "\n\n✅ ПОВНА СХЕМА ГОТОВА!\n")
  (princ)
)

(princ "\n🤖 Схема з PDF завантажена! Введи: drawfullscheme\n")
(princ)
