;; -*- coding: utf-8 -*-
;; СХЕМА ЕЛЕВАТОРА - ПРОСТЕ КРЕСЛЕННЯ
;; Завантаження: (load "D:/autocad project/draw_elevator.lsp")
;; Запуск: (draw-elevator)

(defun c:draw-elevator ()
  (princ "\n🌾 МАЛЮЮ СХЕМУ ЕЛЕВАТОРА...\n")

  ;; Вимикаємо діалоги
  (setvar "CMDECHO" 0)
  (setvar "FILEDIA" 0)

  ;; 1. БУНКЕРИ ПРИЙОМУ H1-H4
  (princ "\n📦 Етап 1/4: Бункери прийому...")
  (setq i 0)
  (repeat 4
    (setq x (* i 15.0))
    (setq y 0.0)

    ;; Трапеція бункера
    (command "._LINE" (list x y) (list (+ x 4) y) "")
    (command "._LINE" (list x y) (list (+ x 1) (+ y 3)) "")
    (command "._LINE" (list (+ x 4) y) (list (+ x 3) (+ y 3)) "")
    (command "._LINE" (list (+ x 1) (+ y 3)) (list (+ x 3) (+ y 3)) "")

    ;; Текст
    (command "._TEXT" "J" "MC" (list (+ x 2) (+ y 1.5)) 1.0 0 (strcat "H" (itoa (+ i 1))))

    (setq i (+ i 1))
  )

  ;; 2. НОРІЇ H5, H6
  (princ "\n⬆️  Етап 2/4: Норії...")
  ;; H5
  (command "._RECTANG" (list 25 5) (list 27 38))
  (command "._TEXT" "J" "MC" (list 26 20) 1.5 0 "H5")

  ;; H6
  (command "._RECTANG" (list 40 5) (list 42 53))
  (command "._TEXT" "J" "MC" (list 41 25) 1.5 0 "H6")

  ;; 3. СИЛОСИ 1-6
  (princ "\n🏗️  Етап 3/4: Силоси...")
  (setq silo-coords '((10 50) (25 50) (40 50) (55 50) (70 50) (85 50)))
  (setq i 0)
  (foreach coord silo-coords
    (setq x (car coord))
    (setq y (cadr coord))

    ;; Циліндр силоса
    (command "._CIRCLE" (list x y) 5.0)
    (command "._CIRCLE" (list x y) 4.0)

    ;; Конусне дно
    (command "._LINE" (list (- x 5) (- y 10)) (list x (- y 13)) "")
    (command "._LINE" (list (+ x 5) (- y 10)) (list x (- y 13)) "")

    ;; Позначка
    (command "._TEXT" "J" "MC" (list x y) 1.2 0 (strcat "S" (itoa (+ i 1))))

    (setq i (+ i 1))
  )

  ;; 4. КОНВЕЄРИ
  (princ "\n🔗 Етап 4/4: Конвеєри...")
  (setq conveyors '(
    ("T7"  25 35 10 48)
    ("T8"  25 35 25 48)
    ("T10" 40 35 40 48)
    ("T11" 40 35 55 48)
    ("T12" 40 35 70 48)
    ("T14" 40 35 85 48)
  ))

  (foreach conv conveyors
    (setq label (nth 0 conv))
    (setq x1 (nth 1 conv))
    (setq y1 (nth 2 conv))
    (setq x2 (nth 3 conv))
    (setq y2 (nth 4 conv))

    ;; Лінія
    (command "._LINE" (list x1 y1) (list x2 y2) "")

    ;; Стрілка
    (if (> (abs (- x2 x1)) (abs (- y2 y1)))
      ;; Горизонтальна
      (progn
        (command "._LINE" (list x2 y2) (list (- x2 1) (+ y2 0.5)) "")
        (command "._LINE" (list x2 y2) (list (- x2 1) (- y2 0.5)) "")
      )
      ;; Вертикальна
      (progn
        (command "._LINE" (list x2 y2) (list (+ x2 0.5) (- y2 1)) "")
        (command "._LINE" (list x2 y2) (list (- x2 0.5) (- y2 1)) "")
      )
    )

    ;; Підпис
    (command "._TEXT" "J" "MC"
      (list (/ (+ x1 x2) 2.0) (+ (/ (+ y1 y2) 2.0) 1))
      0.8 0 label)
  )

  ;; ZOOM EXTENTS
  (princ "\n🔍 Zoom Extents...")
  (command "._ZOOM" "_E")

  (princ "\n\n✅ ГОТОВО! Схема елеватора намальована!\n")
  (princ)
)

;; Автоматичний запуск при завантаженні
(princ "\n========================================")
(princ "\n🌾 СХЕМА ЕЛЕВАТОРА ЗАВАНТАЖЕНА!")
(princ "\n========================================")
(princ "\n\nВведи команду: draw-elevator")
(princ "\nАбо просто: (draw-elevator)")
(princ "\n")
(princ)
