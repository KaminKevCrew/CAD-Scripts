import adsk.core, adsk.fusion, traceback, csv, math

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)

        rootComp = design.rootComponent

        # Ask user to select a sketch
        sketch_sel = ui.selectEntity("Select a sketch with points and path lines", "Sketches")
        sketch = adsk.fusion.Sketch.cast(sketch_sel.entity)

        if not sketch:
            ui.messageBox("No valid sketch selected.")
            return

        points = sketch.sketchPoints
        lines = sketch.sketchCurves.sketchLines

        if points.count < 2 or lines.count < 1:
            ui.messageBox("Sketch must contain multiple points and lines forming a path.")
            return

        # Prompt user to select the starting point
        start_sel = ui.selectEntity("Select the STARTING point (head node)", "SketchPoints")
        start_point = adsk.fusion.SketchPoint.cast(start_sel.entity)
        start_geom = start_point.geometry

        # Prompt user for prefix
        prefix_input = ui.inputBox("Enter designator prefix (e.g., LED, R, C):", "Designator Prefix", "U")

        # Build adjacency map
        def key_from_geom(p):
            return f"{round(p.x,5)}_{round(p.y,5)}"

        adj = {}  # maps point keys to their neighbors
        geom_map = {}  # maps point keys to point objects

        for pt in points:
            k = key_from_geom(pt.geometry)
            geom_map[k] = pt
            adj[k] = []

        for line in lines:
            start_k = key_from_geom(line.startSketchPoint.geometry)
            end_k = key_from_geom(line.endSketchPoint.geometry)
            if start_k in adj and end_k in adj:
                adj[start_k].append(end_k)
                adj[end_k].append(start_k)

        # Traverse path starting from head
        visited = set()
        ordered_points = []

        def dfs(node_key):
            visited.add(node_key)
            ordered_points.append(node_key)
            for neighbor in adj[node_key]:
                if neighbor not in visited:
                    dfs(neighbor)

        start_key = key_from_geom(start_geom)
        dfs(start_key)

        if len(ordered_points) != len(points):
            ui.messageBox("Path traversal did not reach all points. Please ensure the sketch forms a single path.")
            return

        # Prompt user to choose output file
        file_dialog = ui.createFileDialog()
        file_dialog.isMultiSelectEnabled = False
        file_dialog.title = "Save CSV File"
        file_dialog.filter = "CSV files (*.csv)"
        file_dialog.filterIndex = 0

        if file_dialog.showSave() != adsk.core.DialogResults.DialogOK:
            return

        filename = file_dialog.filename

        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Altium standard headers
            writer.writerow(["Designator", "Comment", "Layer", "X Location", "Y Location", "Rotation"])

            for i, key in enumerate(ordered_points):
                pt = geom_map[key]
                x_mm = pt.geometry.x * 10
                y_mm = pt.geometry.y * 10
                writer.writerow([
                    f"{prefix_input}{i+1}", "", "TopLayer", f"{x_mm:.3f}", f"{y_mm:.3f}", "0.0"
                ])

        ui.messageBox(f"CSV file saved to:\n{filename}")

    except Exception as e:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
