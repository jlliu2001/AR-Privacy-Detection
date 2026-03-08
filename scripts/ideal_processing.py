import os
import sys
import glob
import cv2


def ensure_import_path() -> None:
    """
    Ensure the current script directory is on sys.path so that importing
    sibling modules (e.g., pipeline.py) works when run from other locations.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.append(script_dir)


ensure_import_path()
from pipeline import elastic_distort_boxes  # noqa: E402


def list_positive_imgs(data_dir: str,end_file='png'):
    """
    List all .png files under data_dir/positive.
    Returns a sorted list of absolute paths.
    """
    positive_dir = os.path.join(data_dir, 'positive')
    if end_file == 'png':
        pattern = os.path.join(positive_dir, '*.png')
    elif end_file == 'jpg':
        pattern = os.path.join(positive_dir, '*.jpg')
    files = glob.glob(pattern)
    files.sort()
    return files

def list_negative_imgs(data_dir: str,end_file='png'):
    """
    List all .png files under data_dir/positive.
    Returns a sorted list of absolute paths.
    """
    positive_dir = os.path.join(data_dir, 'negative')
    if end_file == 'png':
        pattern = os.path.join(positive_dir, '*.png')
    elif end_file == 'jpg':
        pattern = os.path.join(positive_dir, '*.jpg')
    files = glob.glob(pattern)
    files.sort()
    return files


class RectangleDrawer:
    """
    Interactive rectangle drawer using OpenCV mouse callbacks.
    Collects rectangles and returns them in the format:
    [startX, startY, endX, startY, startX, endY, endX, endY]
    """

    def __init__(self, window_name: str, image):
        self.window_name = window_name
        self.base_image = image
        self.display_image = image.copy()
        self.is_drawing = False
        self.start_point = None
        self.current_point = None
        self.boxes = []
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self._mouse_callback)

    def _mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.is_drawing = True
            self.start_point = (x, y)
            self.current_point = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and self.is_drawing:
            self.current_point = (x, y)
            self._redraw_preview()
        elif event == cv2.EVENT_LBUTTONUP and self.is_drawing:
            self.is_drawing = False
            end_point = (x, y)
            self._commit_rectangle(self.start_point, end_point)
            self._redraw_all()

    def _redraw_preview(self) -> None:
        self.display_image = self.base_image.copy()
        for box in self.boxes:
            x1, y1, x2, _y1, _x1, y2, _x2, _y2 = box
            cv2.rectangle(self.display_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        if self.is_drawing and self.start_point and self.current_point:
            cv2.rectangle(self.display_image, self.start_point, self.current_point, (0, 0, 255), 2)

    def _redraw_all(self) -> None:
        self.display_image = self.base_image.copy()
        for box in self.boxes:
            x1, y1, x2, _y1, _x1, y2, _x2, _y2 = box
            cv2.rectangle(self.display_image, (x1, y1), (x2, y2), (0, 255, 0), 2)

    def _commit_rectangle(self, start, end) -> None:
        x1, y1 = start
        x2, y2 = end
        x_min, x_max = (x1, x2) if x1 <= x2 else (x2, x1)
        y_min, y_max = (y1, y2) if y1 <= y2 else (y2, y1)
        box = [x_min, y_min, x_max, y_min, x_min, y_max, x_max, y_max]
        self.boxes.append(box)

    def run(self):
        instructions = (
            "Draw rectangles with left mouse button.\n"
            "Keys: n=next image, d=delete last, c=clear all, q=quit"
        )
        print(instructions)
        while True:
            cv2.imshow(self.window_name, self.display_image)
            key = cv2.waitKey(20) & 0xFF
            if key == ord('n'):
                return self.boxes
            if key == ord('d'):
                if self.boxes:
                    self.boxes.pop()
                    self._redraw_all()
            if key == ord('c'):
                self.boxes = []
                self._redraw_all()
            if key == ord('q'):
                return None


def process_images_interactively(data_dir: str,end_file='png', is_positive=True) -> None:
    """
    For each .png under data_dir/positive, let user draw rectangles,
    call elastic_distort_boxes with the collected boxes, and save output
    as data_dir/ideal/<img_name>.jpg
    """
    if is_positive:
        images = list_positive_imgs(data_dir,end_file=end_file)
    else:
        images = list_negative_imgs(data_dir,end_file=end_file)
    if not images:
        print("No images found in:", os.path.join(data_dir, 'positive'))
        return
    if is_positive:
        ideal_dir = os.path.join(data_dir, 'positive_ideal')
    else:
        ideal_dir = os.path.join(data_dir, 'negative_ideal')
    os.makedirs(ideal_dir, exist_ok=True)

    for image_path in images:
        image = cv2.imread(image_path)
        if image is None:
            print("Cannot read:", image_path)
            continue

        window_name = f"Annotate: {os.path.basename(image_path)}"
        drawer = RectangleDrawer(window_name, image)
        boxes = drawer.run()
        cv2.destroyWindow(window_name)

        if boxes is None:
            print("User quit.")
            break

        if not boxes:
            print("No rectangles drawn, skipping:", image_path)
            continue

        tmp_out = elastic_distort_boxes(image_path, boxes, tmp_dir=ideal_dir)

        try:
            basename = os.path.splitext(os.path.basename(image_path))[0]
            final_out = os.path.join(ideal_dir, f"{basename}.jpg")
            if os.path.isfile(tmp_out):
                img = cv2.imread(tmp_out)
                if img is not None:
                    cv2.imwrite(final_out, img)
                    print("Saved:", final_out)
                else:
                    print("Failed to load temporary output, leaving as:", tmp_out)
            else:
                print("Expected temporary output not found:", tmp_out)
        except Exception as e:
            print("Failed to save final output:", e)


# def main():
#     if len(sys.argv) < 2:
#         print("Usage: python ideal_processing.py <data_dir>")
#         return
#     data_dir = sys.argv[1]
#     process_images_interactively(data_dir)


if __name__ == '__main__':
    # main()
    data_dir=''
    process_images_interactively(data_dir)


