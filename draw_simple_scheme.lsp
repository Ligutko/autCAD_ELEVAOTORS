;; ПРОСТА СХЕМА ЕЛЕВАТОРА - ТІЛЬКИ БАЗОВІ КОМАНДИ
;; Завантаження: (load "D:/autocad project/draw_simple_scheme.lsp")
;; Запуск: (c:drawscheme)

(defun c:drawscheme ()
  (setvar "CMDECHO" 0)

  (princ "\nМалюю схему...\n")

  ;; Силоси 1-6 (прості кола)
  (princ "\nСилоси...")
  (command "._CIRCLE" (list 15 40) 8)
  (command "._TEXT" (list 13 40) 2 0 "1")

  (command "._CIRCLE" (list 35 40) 8)
  (command "._TEXT" (list 33 40) 2 0 "2")

  (command "._CIRCLE" (list 55 40) 8)
  (command "._TEXT" (list 53 40) 2 0 "3")

  (command "._CIRCLE" (list 75 40) 8)
  (command "._TEXT" (list 73 40) 2 0 "4")

  (command "._CIRCLE" (list 95 40) 8)
  (command "._TEXT" (list 93 40) 2 0 "5")

  (command "._CIRCLE" (list 115 40) 8)
  (command "._TEXT" (list 113 40) 2 0 "6")

  ;; Бункери H1-H4
  (princ "\nБункери...")
  (command "._RECTANG" (list 10 75) (list 16 85))
  (command "._TEXT" (list 11 78) 1.5 0 "H1")

  (command "._RECTANG" (list 30 75) (list 36 85))
  (command "._TEXT" (list 31 78) 1.5 0 "H3")

  (command "._RECTANG" (list 50 75) (list 56 85))
  (command "._TEXT" (list 51 78) 1.5 0 "H4")

  ;; Норії
  (princ "\nНорії...")
  (command "._RECTANG" (list 70 10) (list 74 55))
  (command "._TEXT" (list 71 30) 1.5 0 "H5")

  (command "._RECTANG" (list 95 10) (list 99 70))
  (command "._TEXT" (list 96 40) 1.5 0 "H6")

  ;; Конвеєри (лінії)
  (princ "\nКонвеєри...")
  (command "._LINE" (list 72 55) (list 15 48) "")
  (command "._TEXT" (list 40 52) 1 0 "T7")

  (command "._LINE" (list 72 55) (list 35 48) "")
  (command "._TEXT" (list 50 52) 1 0 "T8")

  (command "._LINE" (list 97 70) (list 55 48) "")
  (command "._TEXT" (list 75 60) 1 0 "T10")

  (command "._LINE" (list 97 70) (list 75 48) "")
  (command "._TEXT" (list 85 60) 1 0 "T11")

  (command "._LINE" (list 97 70) (list 95 48) "")
  (command "._TEXT" (list 96 60) 1 0 "T12")

  (command "._LINE" (list 97 70) (list 115 48) "")
  (command "._TEXT" (list 105 60) 1 0 "T14")

  ;; Zoom
  (command "._ZOOM" "_E")

  (princ "\n\nГОТОВО!\n")
  (princ)
)

(princ "\nСхема завантажена! Введи: drawscheme\n")
(princ)
