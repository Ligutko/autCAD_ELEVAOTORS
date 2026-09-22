;; ПРОФЕСІЙНА ТЕХНОЛОГІЧНА СХЕМА ЕЛЕВАТОРА v2
;; На основі PDF "Технологія 06.06.24.pdf" - Сторінка 1
;; Завантаження: (load "D:/autocad project/draw_PROFESSIONAL_v2.lsp")
;; Запуск: (c:drawpro)

(defun c:drawpro ()
  (setvar "CMDECHO" 0)

  (princ "\n========================================")
  (princ "\n🌾 ПРОФЕСІЙНА СХЕМА ЕЛЕВАТОРА")
  (princ "\n========================================\n")

  ;; ========================================
  ;; ШАРИ
  ;; ========================================
  (princ "\n📐 Створюю шари...")

  ;; Шар обладнання (синій)
  (command "._LAYER" "N" "EQUIPMENT" "C" "5" "EQUIPMENT" "")

  ;; Шар потоків зерна (червоний)
  (command "._LAYER" "N" "FLOW" "C" "1" "FLOW" "")

  ;; Шар повітря (блакитний)
  (command "._LAYER" "N" "AIR" "C" "4" "AIR" "")

  ;; Шар тексту
  (command "._LAYER" "N" "TEXT" "C" "7" "TEXT" "")

  ;; ========================================
  ;; СИЛОСИ 1-6 (детальні з конусом)
  ;; ========================================
  (princ "\n🏗️  Етап 1/5: Силоси MCBY 220.13.B12...")
  (command "._LAYER" "S" "EQUIPMENT" "")

  (setq silo-x-positions '(15 35 55 75 95 115))
  (setq silo-num 1)

  (foreach sx silo-x-positions
    (setq sy 40)

    ;; Циліндрична частина (подвійні кола)
    (command "._CIRCLE" (list sx (+ sy 10)) 7)
    (command "._CIRCLE" (list sx (+ sy 10)) 6.5)

    ;; Вертикальні стінки
    (command "._LINE" (list (- sx 7) sy) (list (- sx 7) (+ sy 10)) "")
    (command "._LINE" (list (+ sx 7) sy) (list (+ sx 7) (+ sy 10)) "")

    ;; Конусне дно
    (command "._LINE" (list (- sx 7) sy) (list sx (- sy 4)) "")
    (command "._LINE" (list (+ sx 7) sy) (list sx (- sy 4)) "")
    (command "._LINE" (list sx (- sy 4)) (list sx (- sy 5)) "")

    ;; Штриховка силоса (вертикальні лінії)
    (setq hatch-x (- sx 6))
    (repeat 12
      (command "._LINE"
        (list hatch-x (+ sy 1))
        (list hatch-x (+ sy 9))
        "")
      (setq hatch-x (+ hatch-x 1))
    )

    ;; Номер силоса
    (command "._LAYER" "S" "TEXT" "")
    (command "._TEXT" (list (- sx 1) (+ sy 10)) 2.5 0 (itoa silo-num))

    ;; Модель
    (command "._TEXT" (list (- sx 4) (+ sy 18)) 0.6 0 "MCBY 220.13.B12")

    (command "._LAYER" "S" "EQUIPMENT" "")
    (setq silo-num (+ silo-num 1))
  )

  ;; ========================================
  ;; БУНКЕРИ H1, H3, H4 (трапеції)
  ;; ========================================
  (princ "\n📦 Етап 2/5: Приймальні бункери...")
  (command "._LAYER" "S" "EQUIPMENT" "")

  (setq hoppers '(
    ("H1" 10 75)
    ("H3" 30 75)
    ("H4" 50 75)
  ))

  (foreach hop hoppers
    (setq h-name (nth 0 hop))
    (setq hx (nth 1 hop))
    (setq hy (nth 2 hop))

    ;; Трапеція
    (command "._LINE" (list hx (+ hy 10)) (list (+ hx 6) (+ hy 10)) "")
    (command "._LINE" (list (+ hx 6) (+ hy 10)) (list (+ hx 5) (+ hy 6)) "")
    (command "._LINE" (list (+ hx 5) (+ hy 6)) (list (+ hx 1) (+ hy 6)) "")
    (command "._LINE" (list (+ hx 1) (+ hy 6)) (list hx (+ hy 10)) "")

    ;; Діагональна штриховка
    (command "._LINE" (list (+ hx 1) (+ hy 6)) (list (+ hx 5) (+ hy 10)) "")
    (command "._LINE" (list hx (+ hy 7)) (list (+ hx 4) (+ hy 10)) "")
    (command "._LINE" (list (+ hx 2) (+ hy 6)) (list (+ hx 6) (+ hy 9)) "")

    ;; Текст
    (command "._LAYER" "S" "TEXT" "")
    (command "._TEXT" (list (+ hx 1) (+ hy 11)) 1.2 0 h-name)
    (command "._TEXT" (list (+ hx 0.5) (+ hy 8)) 0.7 0 "100 т/год")
    (command "._LAYER" "S" "EQUIPMENT" "")
  )

  ;; ========================================
  ;; НОРІЇ H5, H6 (детальні вежі)
  ;; ========================================
  (princ "\n⬆️  Етап 3/5: Норії...")
  (command "._LAYER" "S" "EQUIPMENT" "")

  ;; Норія H5 (33м)
  (setq h5x 70)
  (setq h5y 10)
  (command "._RECTANG" (list h5x h5y) (list (+ h5x 4) (+ h5y 45)))

  ;; Привід вгорі
  (command "._CIRCLE" (list (+ h5x 2) (+ h5y 47)) 1.5)
  (command "._RECTANG" (list (+ h5x 0.5) (+ h5y 45)) (list (+ h5x 3.5) (+ h5y 48)))

  ;; Ковші (маленькі квадратики)
  (setq bucket-y (+ h5y 5))
  (repeat 8
    (command "._RECTANG"
      (list (+ h5x 0.5) bucket-y)
      (list (+ h5x 1.5) (+ bucket-y 1))
      "")
    (setq bucket-y (+ bucket-y 5))
  )

  (command "._LAYER" "S" "TEXT" "")
  (command "._TEXT" (list (+ h5x 0.5) (+ h5y 20)) 1.5 0 "H5")
  (command "._TEXT" (list h5x (+ h5y 17)) 0.7 0 "100 т/год")
  (command "._LAYER" "S" "EQUIPMENT" "")

  ;; Норія H6 (48.7м - вища)
  (setq h6x 95)
  (setq h6y 10)
  (command "._RECTANG" (list h6x h6y) (list (+ h6x 4) (+ h6y 60)))

  ;; Привід
  (command "._CIRCLE" (list (+ h6x 2) (+ h6y 62)) 1.5)
  (command "._RECTANG" (list (+ h6x 0.5) (+ h6y 60)) (list (+ h6x 3.5) (+ h6y 63)))

  ;; Ковші
  (setq bucket-y (+ h6y 5))
  (repeat 11
    (command "._RECTANG"
      (list (+ h6x 0.5) bucket-y)
      (list (+ h6x 1.5) (+ bucket-y 1))
      "")
    (setq bucket-y (+ bucket-y 5))
  )

  (command "._LAYER" "S" "TEXT" "")
  (command "._TEXT" (list (+ h6x 0.5) (+ h6y 30)) 1.5 0 "H6")
  (command "._TEXT" (list h6x (+ h6y 27)) 0.7 0 "100 т/год")
  (command "._LAYER" "S" "EQUIPMENT" "")

  ;; ========================================
  ;; КОНВЕЄРИ (червоні лінії зі стрілками)
  ;; ========================================
  (princ "\n🔗 Етап 4/5: Транспортери...")
  (command "._LAYER" "S" "FLOW" "")

  (setq conveyors '(
    ("T7" 72 55 15 48)
    ("T8" 72 55 35 48)
    ("T10" 97 70 55 48)
    ("T11" 97 70 75 48)
    ("T12" 97 70 95 48)
    ("T14" 97 70 115 48)
  ))

  (foreach conv conveyors
    (setq c-name (nth 0 conv))
    (setq x1 (nth 1 conv))
    (setq y1 (nth 2 conv))
    (setq x2 (nth 3 conv))
    (setq y2 (nth 4 conv))

    ;; Основна лінія
    (command "._LINE" (list x1 y1) (list x2 y2) "")

    ;; Стрілка в кінці (трикутник)
    (setq dx (- x2 x1))
    (setq dy (- y2 y1))
    (setq len (sqrt (+ (* dx dx) (* dy dy))))
    (setq ux (/ dx len))
    (setq uy (/ dy len))

    ;; Вершина стрілки
    (setq arrow-len 2)
    (setq p1 (list x2 y2))
    (setq p2 (list (- x2 (* arrow-len (+ ux (* 0.5 uy))))
                   (- y2 (* arrow-len (- uy (* 0.5 ux))))))
    (setq p3 (list (- x2 (* arrow-len (- ux (* 0.5 uy))))
                   (- y2 (* arrow-len (+ uy (* 0.5 ux))))))

    (command "._SOLID" p1 p2 p3 p1 "")

    ;; Підпис
    (command "._LAYER" "S" "TEXT" "")
    (command "._TEXT"
      (list (/ (+ x1 x2) 2) (+ (/ (+ y1 y2) 2) 1))
      0.9 0 c-name)
    (command "._LAYER" "S" "FLOW" "")
  )

  ;; ========================================
  ;; ФІНАЛЬНІ ШТРИХИ
  ;; ========================================
  (princ "\n📄 Етап 5/5: Оформлення...")

  ;; Рамка
  (command "._LAYER" "S" "TEXT" "")
  (command "._RECTANG" (list 0 0) (list 130 90))

  ;; Заголовок
  (command "._TEXT" (list 35 85) 2.0 0 "Схема технологічного процесу")

  ;; Дата
  (command "._TEXT" (list 110 2) 0.8 0 "05. 06. 2024")
  (command "._TEXT" (list 100 1) 0.7 0 "для ознайомлення")

  ;; ZOOM EXTENTS
  (command "._ZOOM" "_E")

  (princ "\n\n========================================")
  (princ "\n✅ ПРОФЕСІЙНА СХЕМА ГОТОВА!")
  (princ "\n========================================")
  (princ "\n\nЩо намальовано:")
  (princ "\n✓ 6 силосів з конусним дном і штриховкою")
  (princ "\n✓ 3 приймальні бункери (трапеції)")
  (princ "\n✓ 2 норії з ковшами та приводами")
  (princ "\n✓ 6 транспортерів зі стрілками")
  (princ "\n✓ Кольорові шари: EQUIPMENT (синій), FLOW (червоний)")
  (princ "\n")
  (princ)
)

(princ "\n========================================")
(princ "\n🌾 ПРОФЕСІЙНА СХЕМА v2 ЗАВАНТАЖЕНА!")
(princ "\n========================================")
(princ "\n\nВведи команду: drawpro")
(princ "\n")
(princ)
