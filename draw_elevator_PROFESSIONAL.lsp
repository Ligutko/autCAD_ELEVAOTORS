;; -*- coding: utf-8 -*-
;; ПРОФЕСІЙНА ТЕХНОЛОГІЧНА СХЕМА ЕЛЕВАТОРА
;; На основі PDF "Технологія 06.06.24.pdf" - Сторінка 1
;; Завантаження: (load "D:/autocad project/draw_elevator_PROFESSIONAL.lsp")
;; Запуск: (draw-professional-scheme)

(defun c:draw-professional-scheme ()
  (princ "\n🌾 МАЛЮЮ ПРОФЕСІЙНУ ТЕХНОЛОГІЧНУ СХЕМУ...\n")

  ;; Налаштування
  (setvar "CMDECHO" 0)
  (setvar "FILEDIA" 0)

  ;; Створюємо шари
  (princ "\n📐 Створюю шари...")

  ;; Шар для обладнання (синій)
  (command "._LAYER" "N" "EQUIPMENT" "C" "5" "EQUIPMENT" "")

  ;; Шар для потоків (червоний)
  (command "._LAYER" "N" "FLOW_LINES" "C" "1" "FLOW_LINES" "")

  ;; Шар для повітря (синій тонкий)
  (command "._LAYER" "N" "AIR_LINES" "C" "5" "AIR_LINES" "")

  ;; Шар для тексту
  (command "._LAYER" "N" "TEXT" "C" "7" "TEXT" "")

  ;; Шар для рамки
  (command "._LAYER" "N" "BORDER" "C" "8" "BORDER" "")

  ;; Координати (масштаб 1:50 для зручності)
  (setq scale 0.05)
  (setq x-offset 50)
  (setq y-offset 50)

  ;; ========================================
  ;; ЕТАП 1: ПРИЙМАЛЬНІ БУНКЕРИ H1, H3, H4 (ЗВЕРХУ)
  ;; ========================================
  (princ "\n📦 Етап 1/6: Приймальні бункери H1, H3, H4...")
  (command "._LAYER" "S" "EQUIPMENT" "")

  (setq hoppers '(
    ("H1" 10 80 "100 т/год")
    ("H3" 30 80 "100 т/год")
    ("H4" 50 80 "100 т/год")
  ))

  (foreach hopper hoppers
    (setq h-name (nth 0 hopper))
    (setq h-x (nth 1 hopper))
    (setq h-y (nth 2 hopper))
    (setq h-cap (nth 3 hopper))

    ;; Бункер як перевернута трапеція
    (command "._POLYLINE"
      (list h-x (+ h-y 8))
      (list (+ h-x 6) (+ h-y 8))
      (list (+ h-x 5) (+ h-y 4))
      (list (+ h-x 1) (+ h-y 4))
      "C")

    ;; Штриховка бункера
    (command "._HATCH" "ANSI31" (* scale 5) "45" (list (+ h-x 3) (+ h-y 6)) "")

    ;; Текст
    (command "._LAYER" "S" "TEXT" "")
    (command "._TEXT" "J" "MC" (list (+ h-x 3) (+ h-y 9)) 1.5 0 h-name)
    (command "._TEXT" "J" "MC" (list (+ h-x 3) (+ h-y 6)) 0.8 0 h-cap)
    (command "._LAYER" "S" "EQUIPMENT" "")
  )

  ;; ========================================
  ;; ЕТАП 2: ЧЕРВОНА РАМКА ОЧИЩЕННЯ (H1-H3-H4)
  ;; ========================================
  (princ "\n🔴 Етап 2/6: Блок очищення...")
  (command "._LAYER" "S" "FLOW_LINES" "")

  ;; Великий прямокутник навколо H1-H3-H4
  (command "._RECTANG" (list 8 78) (list 58 90))

  ;; Горизонтальна лінія T7
  (command "._LINE" (list 30 76) (list 70 76) "")
  (command "._LAYER" "S" "TEXT" "")
  (command "._TEXT" "J" "MC" (list 50 77) 1.0 0 "T7")
  (command "._TEXT" "J" "MC" (list 50 74) 0.8 0 "100 т/год")

  ;; ========================================
  ;; ЕТАП 3: СИЛОСИ 1-6 (MCBY 220.13.B12)
  ;; ========================================
  (princ "\n🏗️  Етап 3/6: Силоси 1-6...")
  (command "._LAYER" "S" "EQUIPMENT" "")

  (setq silos '(
    (1 15 40)
    (2 35 40)
    (3 55 40)
    (4 75 40)
    (5 95 40)
    (6 115 40)
  ))

  (foreach silo silos
    (setq s-num (nth 0 silo))
    (setq s-x (nth 1 silo))
    (setq s-y (nth 2 silo))

    ;; Великий силос з конусним дном
    ;; Циліндрична частина
    (command "._CIRCLE" (list s-x (+ s-y 15)) 8)
    (command "._CIRCLE" (list s-x (+ s-y 15)) 7)

    ;; Вертикальні лінії стінок
    (command "._LINE" (list (- s-x 8) s-y) (list (- s-x 8) (+ s-y 15)) "")
    (command "._LINE" (list (+ s-x 8) s-y) (list (+ s-x 8) (+ s-y 15)) "")

    ;; Конусне дно
    (command "._LINE" (list (- s-x 8) s-y) (list s-x (- s-y 5)) "")
    (command "._LINE" (list (+ s-x 8) s-y) (list s-x (- s-y 5)) "")

    ;; Штриховка силоса
    (command "._HATCH" "ANSI31" (* scale 3) "45" (list s-x (+ s-y 10)) "")

    ;; Назва та характеристики
    (command "._LAYER" "S" "TEXT" "")
    (command "._TEXT" "J" "MC" (list s-x (+ s-y 15)) 2.0 0 (itoa s-num))
    (command "._TEXT" "J" "MC" (list s-x (+ s-y 25)) 0.8 0 "MCBY 220.13.B12")
    (command "._LAYER" "S" "EQUIPMENT" "")
  )

  ;; ========================================
  ;; ЕТАП 4: НОРІЇ H5 та H6
  ;; ========================================
  (princ "\n⬆️  Етап 4/6: Норії H5 та H6...")
  (command "._LAYER" "S" "EQUIPMENT" "")

  ;; Норія H5 (33м)
  (setq h5-x 70)
  (setq h5-y-bottom 10)
  (setq h5-height 45)

  (command "._RECTANG" (list h5-x h5-y-bottom) (list (+ h5-x 4) (+ h5-y-bottom h5-height)))

  ;; Деталі норії H5
  (command "._CIRCLE" (list (+ h5-x 2) (+ h5-y-bottom h5-height 2)) 1.5)
  (command "._LINE" (list (+ h5-x 2) h5-y-bottom) (list (+ h5-x 2) (+ h5-y-bottom h5-height)) "")

  (command "._LAYER" "S" "TEXT" "")
  (command "._TEXT" "J" "MC" (list (+ h5-x 2) (+ h5-y-bottom 20)) 1.5 0 "H5")
  (command "._TEXT" "J" "MC" (list (+ h5-x 2) (+ h5-y-bottom 17)) 0.8 0 "100 т/год")

  ;; Норія H6 (48.7м - вища)
  (setq h6-x 95)
  (setq h6-y-bottom 10)
  (setq h6-height 60)

  (command "._LAYER" "S" "EQUIPMENT" "")
  (command "._RECTANG" (list h6-x h6-y-bottom) (list (+ h6-x 4) (+ h6-y-bottom h6-height)))

  (command "._CIRCLE" (list (+ h6-x 2) (+ h6-y-bottom h6-height 2)) 1.5)
  (command "._LINE" (list (+ h6-x 2) h6-y-bottom) (list (+ h6-x 2) (+ h6-y-bottom h6-height)) "")

  (command "._LAYER" "S" "TEXT" "")
  (command "._TEXT" "J" "MC" (list (+ h6-x 2) (+ h6-y-bottom 30)) 1.5 0 "H6")
  (command "._TEXT" "J" "MC" (list (+ h6-x 2) (+ h6-y-bottom 27)) 0.8 0 "100 т/год")

  ;; ========================================
  ;; ЕТАП 5: КОНВЕЄРИ (T7-T16)
  ;; ========================================
  (princ "\n🔗 Етап 5/6: Транспортери...")
  (command "._LAYER" "S" "FLOW_LINES" "")

  ;; T7: від норії H5 до силосів
  (command "._LINE" (list 72 55) (list 15 38) "")
  (command "._TEXT" "J" "MC" (list 40 47) 0.8 0 "T7")

  ;; T8
  (command "._LINE" (list 72 55) (list 35 38) "")
  (command "._TEXT" "J" "MC" (list 50 47) 0.8 0 "T8")

  ;; T10: від H6 до силоса 3
  (command "._LINE" (list 97 70) (list 55 38) "")
  (command "._TEXT" "J" "MC" (list 75 55) 0.8 0 "T10")

  ;; T11: до силоса 4
  (command "._LINE" (list 97 70) (list 75 38) "")
  (command "._TEXT" "J" "MC" (list 85 55) 0.8 0 "T11")

  ;; T12: до силоса 5
  (command "._LINE" (list 97 70) (list 95 38) "")
  (command "._TEXT" "J" "MC" (list 96 55) 0.8 0 "T12")

  ;; T14: до силоса 6
  (command "._LINE" (list 97 70) (list 115 38) "")
  (command "._TEXT" "J" "MC" (list 105 55) 0.8 0 "T14")

  ;; Стрілки напрямку потоку
  (foreach line-end '((15 38) (35 38) (55 38) (75 38) (95 38) (115 38))
    (setq ex (car line-end))
    (setq ey (cadr line-end))
    (command "._SOLID"
      (list ex ey)
      (list (- ex 1) (+ ey 1))
      (list (- ex 1) (- ey 1))
      (list ex ey)
      "")
  )

  ;; ========================================
  ;; ЕТАП 6: РАМКА КРЕСЛЕННЯ
  ;; ========================================
  (princ "\n📄 Етап 6/6: Рамка та штамп...")
  (command "._LAYER" "S" "BORDER" "")

  ;; Зовнішня рамка A3
  (command "._RECTANG" (list 0 0) (list 140 100))

  ;; Заголовок
  (command "._LAYER" "S" "TEXT" "")
  (command "._TEXT" "J" "MC" (list 70 95) 2.5 0 "Схема технологічного процесу")

  ;; Дата
  (command "._TEXT" "J" "BR" (list 135 3) 1.0 0 "05. 06. 2024")
  (command "._TEXT" "J" "BR" (list 135 1) 0.8 0 "для ознайомлення")

  ;; ZOOM EXTENTS
  (princ "\n🔍 Zoom Extents...")
  (command "._ZOOM" "_E")

  (princ "\n\n============================================================")
  (princ "\n✅ ПРОФЕСІЙНА СХЕМА ГОТОВА!")
  (princ "\n============================================================")
  (princ "\n\nЩо намальовано:")
  (princ "\n✓ Приймальні бункери H1, H3, H4")
  (princ "\n✓ 6 силосів MCBY 220.13.B12")
  (princ "\n✓ Норії H5 (33м) та H6 (48.7м)")
  (princ "\n✓ Транспортери T7, T8, T10-T14")
  (princ "\n✓ Шари: EQUIPMENT, FLOW_LINES, TEXT, BORDER")
  (princ "\n")
  (princ)
)

;; Автозапуск
(princ "\n========================================")
(princ "\n🌾 ПРОФЕСІЙНА СХЕМА ЗАВАНТАЖЕНА!")
(princ "\n========================================")
(princ "\n\nВведи: draw-professional-scheme")
(princ "\n")
(princ)
