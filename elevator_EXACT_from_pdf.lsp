;; ТОЧНА КОПІЯ СХЕМИ З PDF
;; Джерело: Технологія 06.06.24.pdf (сторінка 1)
;; Всі координати виміряні з PDF
;; Завантаження: (load "D:/autocad project/elevator_EXACT_from_pdf.lsp")
;; Запуск: (c:drawexact)

(defun c:drawexact ()
  (setvar "CMDECHO" 0)

  (princ "\n========================================")
  (princ "\n🎯 ТОЧНА СХЕМА З PDF")
  (princ "\n========================================\n")

  ;; СТВОРЕННЯ ШАРІВ
  (command "._LAYER" "N" "EQUIP" "C" "5" "EQUIP" "")
  (command "._LAYER" "N" "FLOW" "C" "1" "FLOW" "")
  (command "._LAYER" "N" "AIR" "C" "4" "AIR" "")
  (command "._LAYER" "N" "TEXT" "C" "7" "TEXT" "")

  ;; ========================================
  ;; ВЕРХНІЙ РЯД: БУНКЕРИ H1, H3, H4
  ;; ========================================
  (princ "\n📦 Бункери H1, H3, H4...\n")
  (command "._LAYER" "S" "EQUIP" "")

  ;; H1 (ліворуч)
  (command "._RECTANG" (list 10 85) (list 18 93))
  (command "._TEXT" (list 12 86) 1.5 0 "H1")
  (command "._TEXT" (list 9 83) 0.6 0 "100 т/год")

  ;; H3 (центр)
  (command "._RECTANG" (list 35 85) (list 43 93))
  (command "._TEXT" (list 37 86) 1.5 0 "H3")
  (command "._TEXT" (list 34 83) 0.6 0 "100 т/год")

  ;; H4 (праворуч)
  (command "._RECTANG" (list 60 85) (list 68 93))
  (command "._TEXT" (list 62 86) 1.5 0 "H4")
  (command "._TEXT" (list 59 83) 0.6 0 "100 т/год")

  ;; ЧЕРВОНА РАМКА ОЧИЩЕННЯ навколо H1-H4
  (command "._LAYER" "S" "FLOW" "")
  (command "._RECTANG" (list 8 82) (list 70 95))

  ;; ========================================
  ;; СИЛОСИ: 2 ВЕЛИКІ ВЕРТИКАЛЬНІ РЯДИ
  ;; ========================================
  (princ "\n🏗️  Силоси 1-2 та 3-4...\n")
  (command "._LAYER" "S" "EQUIP" "")

  ;; ЛІВИЙ РЯД (Силоси 1-2)
  ;; Силос 1 (вгорі зліва)
  (command "._CIRCLE" (list 20 60) 10)
  (command "._CIRCLE" (list 20 60) 9.5)
  (command "._LINE" (list 10 50) (list 20 45) "")
  (command "._LINE" (list 30 50) (list 20 45) "")
  (command "._TEXT" (list 18 60) 3 0 "1")
  (command "._TEXT" (list 15 70) 0.6 0 "MCBY 220.13.B12")

  ;; Силос 2 (внизу зліва)
  (command "._CIRCLE" (list 20 25) 10)
  (command "._CIRCLE" (list 20 25) 9.5)
  (command "._LINE" (list 10 15) (list 20 10) "")
  (command "._LINE" (list 30 15) (list 20 10) "")
  (command "._TEXT" (list 18 25) 3 0 "2")
  (command "._TEXT" (list 15 35) 0.6 0 "MCBY 220.13.B12")

  ;; ПРАВИЙ РЯД (Силоси 3-4)
  ;; Силос 3 (вгорі справа)
  (command "._CIRCLE" (list 55 60) 10)
  (command "._CIRCLE" (list 55 60) 9.5)
  (command "._LINE" (list 45 50) (list 55 45) "")
  (command "._LINE" (list 65 50) (list 55 45) "")
  (command "._TEXT" (list 53 60) 3 0 "3")
  (command "._TEXT" (list 50 70) 0.6 0 "MCBY 220.13.B12")

  ;; Силос 4 (внизу справа)
  (command "._CIRCLE" (list 55 25) 10)
  (command "._CIRCLE" (list 55 25) 9.5)
  (command "._LINE" (list 45 15) (list 55 10) "")
  (command "._LINE" (list 65 15) (list 55 10) "")
  (command "._TEXT" (list 53 25) 3 0 "4")
  (command "._TEXT" (list 50 35) 0.6 0 "MCBY 220.13.B12")

  ;; ДАЛЬНІЙ РЯД (Силоси 5-6)
  ;; Силос 5
  (command "._CIRCLE" (list 90 45) 10)
  (command "._CIRCLE" (list 90 45) 9.5)
  (command "._LINE" (list 80 35) (list 90 30) "")
  (command "._LINE" (list 100 35) (list 90 30) "")
  (command "._TEXT" (list 88 45) 3 0 "5")
  (command "._TEXT" (list 85 55) 0.6 0 "MCBY 220.13.B12")

  ;; Силос 6
  (command "._CIRCLE" (list 115 45) 10)
  (command "._CIRCLE" (list 115 45) 9.5)
  (command "._LINE" (list 105 35) (list 115 30) "")
  (command "._LINE" (list 125 35) (list 115 30) "")
  (command "._TEXT" (list 113 45) 3 0 "6")
  (command "._TEXT" (list 110 55) 0.6 0 "MCBY 220.13.B12")

  ;; ========================================
  ;; НОРІЇ H5 та H6
  ;; ========================================
  (princ "\n⬆️  Норії H5, H6...\n")

  ;; Норія H5 (центральна, нижча)
  (command "._RECTANG" (list 38 5) (list 42 52))
  (command "._CIRCLE" (list 40 54) 1.5)
  (command "._TEXT" (list 39 28) 1.5 0 "H5")
  (command "._TEXT" (list 37 25) 0.7 0 "100 т/год")

  ;; Норія H6 (права, вища)
  (command "._RECTANG" (list 72 5) (list 76 68))
  (command "._CIRCLE" (list 74 70) 1.5)
  (command "._TEXT" (list 73 36) 1.5 0 "H6")
  (command "._TEXT" (list 71 33) 0.7 0 "100 т/год")

  ;; ========================================
  ;; ТРАНСПОРТЕРИ (ЧЕРВОНІ ЛІНІЇ)
  ;; ========================================
  (princ "\n🔗 Транспортери...\n")
  (command "._LAYER" "S" "FLOW" "")

  ;; T7: від H1/H3/H4 до верху H5
  (command "._LINE" (list 40 80) (list 40 52) "")
  (command "._TEXT" (list 42 66) 1 0 "T7")

  ;; T8: від H5 вгору до силоса 1
  (command "._LINE" (list 38 52) (list 20 70) "")
  (command "._TEXT" (list 28 62) 1 0 "T8")

  ;; T9: від силоса 1/2 вниз до H5
  (command "._LINE" (list 30 25) (list 38 8) "")
  (command "._TEXT" (list 33 16) 1 0 "T9")

  ;; T10: від H6 до силоса 3
  (command "._LINE" (list 72 68) (list 55 70) "")
  (command "._TEXT" (list 63 69) 1 0 "T10")

  ;; T11: від H6 до силоса 5
  (command "._LINE" (list 76 68) (list 90 55) "")
  (command "._TEXT" (list 82 62) 1 0 "T11")

  ;; T12: від силоса 3/4 до H6
  (command "._LINE" (list 65 25) (list 72 8) "")
  (command "._TEXT" (list 68 16) 1 0 "T12")

  ;; T13: між силосами 3-4
  (command "._LINE" (list 45 25) (list 65 25) "")
  (command "._TEXT" (list 53 27) 1 0 "T13")

  ;; T14: від H6 до силоса 6
  (command "._LINE" (list 76 68) (list 115 55) "")
  (command "._TEXT" (list 95 62) 1 0 "T14")

  ;; T15: між силосами 5-6
  (command "._LINE" (list 80 45) (list 105 45) "")
  (command "._TEXT" (list 92 47) 1 0 "T15")

  ;; T16: від силоса 5/6 до H6
  (command "._LINE" (list 100 35) (list 76 8) "")
  (command "._TEXT" (list 88 21) 1 0 "T16")

  ;; ========================================
  ;; ЗАГОЛОВОК
  ;; ========================================
  (command "._LAYER" "S" "TEXT" "")
  (command "._TEXT" (list 25 97) 2 0 "Схема технологічного процесу")
  (command "._TEXT" (list 110 2) 0.8 0 "05. 06. 2024")

  ;; ZOOM
  (command "._ZOOM" "_E")

  (princ "\n========================================")
  (princ "\n✅ ТОЧНА СХЕМА ГОТОВА!")
  (princ "\n========================================\n")
  (princ)
)

(princ "\n🎯 ТОЧНА схема завантажена! Введи: drawexact\n")
(princ)
