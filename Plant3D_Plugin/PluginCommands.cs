using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Geometry;
using Autodesk.AutoCAD.Runtime;
using Newtonsoft.Json;
using System;
using System.IO;

namespace GrainElevatorPlugin
{
    public class PluginCommands : IExtensionApplication
    {
        // Ініціалізація плагіна
        public void Initialize()
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            Editor ed = doc.Editor;
            ed.WriteMessage("\n*** Grain Elevator Plugin Loaded ***");
            ed.WriteMessage("\nAvailable commands:");
            ed.WriteMessage("\n  CREATESILO - Create parametric silo");
            ed.WriteMessage("\n  CREATEELEVATOR - Create bucket elevator");
            ed.WriteMessage("\n  GENERATESCHEME - Generate complete scheme from JSON");
            ed.WriteMessage("\n  SCALESILOS - Scale selected silos");
        }

        public void Terminate()
        {
            // Cleanup
        }

        // Команда: Створити силос
        [CommandMethod("CREATESILO")]
        public void CreateSilo()
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            Database db = doc.Database;
            Editor ed = doc.Editor;

            // Запитати параметри у користувача
            PromptDoubleOptions diameterOpt = new PromptDoubleOptions("\nEnter silo diameter (mm): ");
            diameterOpt.DefaultValue = 22000;
            diameterOpt.AllowNegative = false;
            PromptDoubleResult diameterRes = ed.GetDouble(diameterOpt);
            if (diameterRes.Status != PromptStatus.OK) return;

            PromptDoubleOptions heightOpt = new PromptDoubleOptions("\nEnter silo height (mm): ");
            heightOpt.DefaultValue = 24000;
            heightOpt.AllowNegative = false;
            PromptDoubleResult heightRes = ed.GetDouble(heightOpt);
            if (heightRes.Status != PromptStatus.OK) return;

            PromptPointOptions posOpt = new PromptPointOptions("\nSpecify insertion point: ");
            PromptPointResult posRes = ed.GetPoint(posOpt);
            if (posRes.Status != PromptStatus.OK) return;

            PromptStringOptions tagOpt = new PromptStringOptions("\nEnter equipment tag (e.g., MSVU-220.13): ");
            tagOpt.DefaultValue = "MSVU-220.13";
            PromptResult tagRes = ed.GetString(tagOpt);
            if (tagRes.Status != PromptStatus.OK) return;

            double diameter = diameterRes.Value;
            double height = heightRes.Value;
            Point3d insertionPoint = posRes.Value;
            string tag = tagRes.StringResult;

            // Створити силос
            using (Transaction tr = db.TransactionManager.StartTransaction())
            {
                BlockTable bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                BlockTableRecord btr = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);

                // Намалювати основний циліндр (вид збоку)
                double radius = diameter / 2;

                // Ліва вертикальна лінія
                Line leftLine = new Line(
                    new Point3d(insertionPoint.X - radius, insertionPoint.Y, 0),
                    new Point3d(insertionPoint.X - radius, insertionPoint.Y + height, 0)
                );
                leftLine.Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(
                    Autodesk.AutoCAD.Colors.ColorMethod.ByColor, 5); // Blue

                // Права вертикальна лінія
                Line rightLine = new Line(
                    new Point3d(insertionPoint.X + radius, insertionPoint.Y, 0),
                    new Point3d(insertionPoint.X + radius, insertionPoint.Y + height, 0)
                );
                rightLine.Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(
                    Autodesk.AutoCAD.Colors.ColorMethod.ByColor, 5);

                // Нижня дуга (конус)
                Arc bottomArc = new Arc(
                    new Point3d(insertionPoint.X, insertionPoint.Y, 0),
                    radius,
                    Math.PI,
                    0
                );
                bottomArc.Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(
                    Autodesk.AutoCAD.Colors.ColorMethod.ByColor, 5);

                // Верхня дуга (дах)
                Arc topArc = new Arc(
                    new Point3d(insertionPoint.X, insertionPoint.Y + height, 0),
                    radius,
                    0,
                    Math.PI
                );
                topArc.Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(
                    Autodesk.AutoCAD.Colors.ColorMethod.ByColor, 5);

                // Додати до креслення
                btr.AppendEntity(leftLine);
                btr.AppendEntity(rightLine);
                btr.AppendEntity(bottomArc);
                btr.AppendEntity(topArc);

                tr.AddNewlyCreatedDBObject(leftLine, true);
                tr.AddNewlyCreatedDBObject(rightLine, true);
                tr.AddNewlyCreatedDBObject(bottomArc, true);
                tr.AddNewlyCreatedDBObject(topArc, true);

                // Додати текст (позначка)
                DBText text = new DBText();
                text.Position = new Point3d(insertionPoint.X, insertionPoint.Y + height / 2, 0);
                text.Height = 500;
                text.TextString = tag;
                text.HorizontalMode = TextHorizontalMode.TextCenter;
                text.AlignmentPoint = text.Position;

                btr.AppendEntity(text);
                tr.AddNewlyCreatedDBObject(text, true);

                // Додати Extended Data для зберігання параметрів
                leftLine.XData = CreateSiloXData(diameter, height, tag);

                tr.Commit();

                ed.WriteMessage($"\nSilo created: {tag}, Diameter={diameter}mm, Height={height}mm");

                // Обчислити об'єм
                double volume = Math.PI * Math.Pow(radius, 2) * height / 1000000000; // m³
                ed.WriteMessage($"\nCalculated volume: {volume:F2} m³");
            }
        }

        // Команда: Згенерувати схему з JSON
        [CommandMethod("GENERATESCHEME")]
        public void GenerateScheme()
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            Editor ed = doc.Editor;

            // Запитати шлях до JSON файлу
            PromptStringOptions fileOpt = new PromptStringOptions("\nEnter path to scheme JSON file: ");
            fileOpt.DefaultValue = @"d:\autocad project\scheme_config.json";
            PromptResult fileRes = ed.GetString(fileOpt);
            if (fileRes.Status != PromptStatus.OK) return;

            string jsonPath = fileRes.StringResult;

            if (!File.Exists(jsonPath))
            {
                ed.WriteMessage($"\nError: File not found: {jsonPath}");
                return;
            }

            try
            {
                // Прочитати JSON
                string json = File.ReadAllText(jsonPath);
                SchemeConfig config = JsonConvert.DeserializeObject<SchemeConfig>(json);

                ed.WriteMessage($"\nGenerating scheme: {config.Name}");
                ed.WriteMessage($"\nSilos count: {config.Silos.Length}");

                // Згенерувати силоси
                foreach (var silo in config.Silos)
                {
                    CreateSiloProgrammatically(silo.X, silo.Y, silo.Diameter, silo.Height, silo.Tag);
                }

                ed.WriteMessage("\nScheme generated successfully!");

            }
            catch (System.Exception ex)
            {
                ed.WriteMessage($"\nError: {ex.Message}");
            }
        }

        // Команда: Масштабувати силоси
        [CommandMethod("SCALESILOS")]
        public void ScaleSilos()
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            Database db = doc.Database;
            Editor ed = doc.Editor;

            // Попросити вибрати об'єкти
            PromptSelectionOptions selOpt = new PromptSelectionOptions();
            selOpt.MessageForAdding = "\nSelect silos to scale: ";
            PromptSelectionResult selRes = ed.GetSelection(selOpt);
            if (selRes.Status != PromptStatus.OK) return;

            // Запитати коефіцієнт масштабування
            PromptDoubleOptions scaleOpt = new PromptDoubleOptions("\nEnter scale factor (e.g., 1.25 for 25% increase): ");
            scaleOpt.DefaultValue = 1.25;
            scaleOpt.AllowNegative = false;
            PromptDoubleResult scaleRes = ed.GetDouble(scaleOpt);
            if (scaleRes.Status != PromptStatus.OK) return;

            double scaleFactor = scaleRes.Value;

            // Запитати базову точку
            PromptPointOptions baseOpt = new PromptPointOptions("\nSpecify base point for scaling: ");
            PromptPointResult baseRes = ed.GetPoint(baseOpt);
            if (baseRes.Status != PromptStatus.OK) return;

            Point3d basePoint = baseRes.Value;

            using (Transaction tr = db.TransactionManager.StartTransaction())
            {
                int scaledCount = 0;

                foreach (SelectedObject selObj in selRes.Value)
                {
                    Entity ent = tr.GetObject(selObj.ObjectId, OpenMode.ForWrite) as Entity;
                    if (ent != null)
                    {
                        // Створити матрицю масштабування
                        Matrix3d scaleMatrix = Matrix3d.Scaling(scaleFactor, basePoint);

                        // Застосувати трансформацію
                        ent.TransformBy(scaleMatrix);

                        scaledCount++;
                    }
                }

                tr.Commit();

                ed.WriteMessage($"\nScaled {scaledCount} objects by factor {scaleFactor}");
            }
        }

        // Допоміжні методи

        private void CreateSiloProgrammatically(double x, double y, double diameter, double height, string tag)
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            Database db = doc.Database;

            using (Transaction tr = db.TransactionManager.StartTransaction())
            {
                BlockTable bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                BlockTableRecord btr = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);

                double radius = diameter / 2;
                Point3d insertionPoint = new Point3d(x, y, 0);

                // Аналогічно CreateSilo() але без запитів користувача
                Line leftLine = new Line(
                    new Point3d(insertionPoint.X - radius, insertionPoint.Y, 0),
                    new Point3d(insertionPoint.X - radius, insertionPoint.Y + height, 0)
                );
                leftLine.Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(
                    Autodesk.AutoCAD.Colors.ColorMethod.ByColor, 5);

                btr.AppendEntity(leftLine);
                tr.AddNewlyCreatedDBObject(leftLine, true);

                // Права лінія
                Line rightLine = new Line(
                    new Point3d(insertionPoint.X + radius, insertionPoint.Y, 0),
                    new Point3d(insertionPoint.X + radius, insertionPoint.Y + height, 0)
                );
                rightLine.Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(
                    Autodesk.AutoCAD.Colors.ColorMethod.ByColor, 5);
                btr.AppendEntity(rightLine);
                tr.AddNewlyCreatedDBObject(rightLine, true);

                // Нижня дуга
                Arc bottomArc = new Arc(
                    new Point3d(insertionPoint.X, insertionPoint.Y, 0),
                    radius,
                    Math.PI,
                    0
                );
                bottomArc.Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(
                    Autodesk.AutoCAD.Colors.ColorMethod.ByColor, 5);
                btr.AppendEntity(bottomArc);
                tr.AddNewlyCreatedDBObject(bottomArc, true);

                // Верхня дуга
                Arc topArc = new Arc(
                    new Point3d(insertionPoint.X, insertionPoint.Y + height, 0),
                    radius,
                    0,
                    Math.PI
                );
                topArc.Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(
                    Autodesk.AutoCAD.Colors.ColorMethod.ByColor, 5);
                btr.AppendEntity(topArc);
                tr.AddNewlyCreatedDBObject(topArc, true);

                // Текст позначки
                DBText text = new DBText();
                text.Position = new Point3d(insertionPoint.X, insertionPoint.Y + height / 2, 0);
                text.Height = 500;
                text.TextString = tag;
                text.HorizontalMode = TextHorizontalMode.TextCenter;
                text.AlignmentPoint = text.Position;
                btr.AppendEntity(text);
                tr.AddNewlyCreatedDBObject(text, true);

                tr.Commit();
            }
        }

        private ResultBuffer CreateSiloXData(double diameter, double height, string tag)
        {
            ResultBuffer rb = new ResultBuffer(
                new TypedValue((int)DxfCode.ExtendedDataRegAppName, "GrainElevatorPlugin"),
                new TypedValue((int)DxfCode.ExtendedDataReal, diameter),
                new TypedValue((int)DxfCode.ExtendedDataReal, height),
                new TypedValue((int)DxfCode.ExtendedDataAsciiString, tag)
            );
            return rb;
        }
    }

    // Класи для JSON конфігурації
    public class SchemeConfig
    {
        public string Name { get; set; }
        public SiloConfig[] Silos { get; set; }
    }

    public class SiloConfig
    {
        public double X { get; set; }
        public double Y { get; set; }
        public double Diameter { get; set; }
        public double Height { get; set; }
        public string Tag { get; set; }
    }
}
