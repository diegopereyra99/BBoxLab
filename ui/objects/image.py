import time
import customtkinter
from PIL import Image, ImageDraw
from customtkinter import CTkImage
import numpy as np
from .annotations import Annotation

class ZoomableImage(customtkinter.CTkLabel):
    """
    Label in which the images can be zoomed into.
    """
    def __init__(self, master=None, **kwargs):
        self.sensibility = kwargs.pop('sensibility', 0.2)
        self.max_zoom = kwargs.pop('max_zoom', 15.0)
        super().__init__(master, text='', **kwargs)
        self.pil_image = None
        self.__old_event = None
        self.width = kwargs.get('width', 500)
        self.height = kwargs.get('height', 500)
        self.min_scale = 0.0
        self.current_view = None
        
        self.create_bindings()
        self.reset_transform()

    def create_bindings(self):
        self.bind("<Button-1>", self.mouse_down_left)                   # MouseDown
        self.bind("<B1-Motion>", self.mouse_move_left)                  # MouseDrag
        self.bind("<MouseWheel>", self.mouse_wheel)                     # MouseWheel
        self.bind("<Button-2>", self.mouse_down_left)             # MouseUp
        self.bind("<B2-Motion>", self.mouse_wheel_move)             # MouseDrag
        self.bind("<ButtonRelease-2>", self.mouse_wheel_up)           # MouseUp

    def set_image(self, filename=None, pil_image=None):
        self.pil_image = pil_image if pil_image else Image.open(filename)
        self.min_scale = min(self.width / self.pil_image.width, self.height / self.pil_image.height)
        self.zoom_fit()
        self.draw_image(self.pil_image)

    def resize_frame(self, width, height):
        self.width = width
        self.height = height
        if self.pil_image is None:
            return
        self.min_scale = min(self.width / self.pil_image.width, self.height / self.pil_image.height)
        self.zoom_fit()
        self.redraw_image()

    # -------------------------------------------------------------------------------
    # Mouse events
    # -------------------------------------------------------------------------------
    def mouse_down_left(self, event):
        self.__old_event = event

    def mouse_move_left(self, event):
        if self.pil_image is None:
            return
        
        self.translate(event.x - self.__old_event.x, event.y - self.__old_event.y) if self.__old_event else None
        self.redraw_image()
        self.__old_event = event

    def mouse_double_click_left(self, event):
        if self.pil_image is None:
            return
        self.zoom_fit()
        self.redraw_image() 

    def mouse_wheel(self, event):
        if self.pil_image is None:
            return

        if event.delta < 0:
            scaling = 1 / (1 + self.sensibility)
            if scaling < self.min_scale / self.current_scale:
                scaling = self.min_scale / self.current_scale

            # Rotate upwards and shrink
            self.scale_at(scaling, event.x, event.y)
        else:
            scaling = 1 + self.sensibility
            if scaling > self.min_scale / self.current_scale * self.max_zoom:
                scaling = self.min_scale / self.current_scale * self.max_zoom

            # Rotate downwards and enlarge
            self.scale_at(scaling, event.x, event.y)
        
        self.redraw_image()

    def mouse_wheel_move(self, event):
        if self.pil_image is None:
            return
        
        dst = self.current_view
        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 50))

        w = event.x - self.__old_event.x
        h = event.y - self.__old_event.y
        # scale = max(abs(w) / self.width, abs(h) / self.height)
        # if scale == 0:
        #     return
        # w = scale * self.width * np.sign(w)
        # h = scale * self.height * np.sign(h)

        x1 = min(self.__old_event.x, self.__old_event.x + w)
        y1 = min(self.__old_event.y, self.__old_event.y + h)
        x2 = max(self.__old_event.x, self.__old_event.x + w)
        y2 = max(self.__old_event.y, self.__old_event.y + h)

        draw = ImageDraw.Draw(overlay)
        draw.rectangle((x1, y1, x2, y2), outline='#ffffff40', fill='#ffffff00', width=2)

        dst = Image.alpha_composite(dst.convert('RGBA'), overlay)

        self.show_image(dst)

    def mouse_wheel_up(self, event):
        if self.pil_image is None:
            return
        
        w = abs(event.x - self.__old_event.x) / self.current_scale
        h = abs(event.y - self.__old_event.y) / self.current_scale
        
        if w == 0 or h == 0:
            self.zoom_fit()
            self.redraw_image()
            return


        scale = min(self.width / w, self.height / h) / self.min_scale
        
        x1 = min(self.__old_event.x, event.x)
        y1 = min(self.__old_event.y, event.y)
        x2 = max(self.__old_event.x, event.x)
        y2 = max(self.__old_event.y, event.y)

        x, y = self.to_image_point((x1 + x2) / 2, (y1 + y2) / 2)

        ret = self.go_to_point(x, y, scale)
        if not ret:
            self.redraw_image()

    # -------------------------------------------------------------------------------
    # Affine Transformation for Image Display
    # -------------------------------------------------------------------------------

    def reset_transform(self):
        self.mat_affine = np.eye(3)

    @property
    def current_scale(self):
        return self.mat_affine[0, 0]

    def translate(self, offset_x, offset_y, zoom=False):
        mat = np.eye(3)
        mat[0, 2] = float(offset_x)
        mat[1, 2] = float(offset_y)
        
        scale = self.mat_affine[0, 0]
        current_h = scale * self.pil_image.height
        current_w = scale * self.pil_image.width
        self.mat_affine = np.dot(mat, self.mat_affine)

        if not zoom:
            if current_w < self.width:
                # if (self.mat_affine[0, 2]) > self.width - current_w:
                #     self.mat_affine[0, 2] = self.width - current_w
                # elif self.mat_affine[0, 2] < 0:
                #     self.mat_affine[0, 2] = 0
                self.mat_affine[0, 2] = self.width / 2 - current_w / 2
            else:
                if (self.mat_affine[0, 2]) > 0:
                    self.mat_affine[0, 2] = 0
                elif (self.mat_affine[0, 2]) < -current_w + self.width:
                    self.mat_affine[0, 2] = -current_w + self.width
            if current_h < self.height:
                # if (self.mat_affine[1, 2]) > self.height - current_h:
                #     self.mat_affine[1, 2] = self.height - current_h
                # elif self.mat_affine[1, 2] < 0:
                #     self.mat_affine[1, 2] = 0
                self.mat_affine[1, 2] = self.height / 2 - current_h / 2
            else:
                if (self.mat_affine[1, 2]) > 0:
                    self.mat_affine[1, 2] = 0
                elif (self.mat_affine[1, 2]) < -current_h + self.height:
                    self.mat_affine[1, 2] = -current_h + self.height

    def scale(self, scale: float):
        mat = np.eye(3)
        mat[0, 0] = scale
        mat[1, 1] = scale
        self.mat_affine = np.dot(mat, self.mat_affine)

    def scale_at(self, scale: float, cx: float, cy: float):
        self.translate(-cx, -cy, True)
        self.scale(scale)
        self.translate(cx, cy)

    def zoom_fit(self):
        self.update()

        if (self.pil_image.width * self.pil_image.height <= 0) or (self.width * self.height <= 0):
            return

        self.reset_transform()

        # Calculate the offsets to center the image
        offsetx = (self.width - self.pil_image.width * self.min_scale) / 2
        offsety = (self.height - self.pil_image.height * self.min_scale) / 2

        self.scale(self.min_scale)
        self.translate(offsetx, offsety)

    def go_to_point(self, x, y, scale=None, animate=True, **kwargs):
        if self.pil_image is None:
            return

        if scale is None:
            scale = self.max_zoom * self.min_scale
        else:
            scale = max(min(scale, self.max_zoom), 1) * self.min_scale

        initial_affine = self.mat_affine.copy()
        self.reset_transform()
        self.translate(-x, -y, True)
        self.scale(scale)
        self.translate(self.width / 2, self.height / 2)
        final_affine = self.mat_affine.copy()

        if (initial_affine == final_affine).all():
            return False

        if animate:
            self.make_animation(final_affine, initial_affine, **kwargs)
                
        self.redraw_image()
        return True


    def to_image_point(self, x, y):
        '''Convert coordinates from the canvas to the image'''
        if self.pil_image is None:
            return []
        mat_inv = np.linalg.inv(self.mat_affine)
        image_point = np.dot(mat_inv, (x, y, 1.))
        if image_point[0] < 0 or image_point[1] < 0 or image_point[0] > self.pil_image.width or image_point[1] > self.pil_image.height:
            return []
        return image_point[:2]
    
    # -------------------------------------------------------------------------------
    # Drawing 
    # -------------------------------------------------------------------------------

    def get_image_transformed(self, pil_image):
        if pil_image is None:
            return
        
        mat_inv = np.linalg.inv(self.mat_affine)

        affine_inv = (
            mat_inv[0, 0], mat_inv[0, 1], mat_inv[0, 2],
            mat_inv[1, 0], mat_inv[1, 1], mat_inv[1, 2]
        )

        dst = pil_image.copy()

        dst = dst.transform(
            (self.width, self.height),
            Image.AFFINE,
            affine_inv,
            Image.BILINEAR
        )

        return dst

    def draw_image(self, pil_image):
        if self.pil_image is None:
            return

        self.pil_image = pil_image

        dst = self.get_image_transformed(self.pil_image)

        self.show_image(dst)

    def show_image(self, pil_view=None):
        if pil_view is None:
            pil_view = self.current_view
        ctk_image = CTkImage(light_image=pil_view, size=(self.width, self.height))
        self.configure(image=ctk_image)

    def redraw_image(self):
        '''Redraw the image'''
        if self.pil_image is None:
            return
        self.draw_image(self.pil_image)

    def make_animation(self, final_affine, initial_affine=None, duration='auto', fps=20):
        if initial_affine is None:
            initial_affine = self.mat_affine
        
        if duration == 'auto':
            try:
                inv0 = np.linalg.inv(initial_affine)
                inv1 = np.linalg.inv(final_affine)
                p0, p1 = [0, 0, 1], [self.width, self.height, 1]
                vi = np.dot(inv0, np.array([p0, p1]).T)
                vf = np.dot(inv1, np.array([p0, p1]).T)
                dists = np.linalg.norm(vf - vi, axis=0) * self.min_scale

                duration = np.log10(dists.sum()) / 5
                # raise Exception
            except:
                duration = 1


        total_frames = int(duration * fps + 0.5)
        delta_affine = (final_affine - initial_affine) / total_frames

        for frame_number in range(total_frames + 1):
            start = time.time()
            curr = initial_affine + delta_affine * frame_number
            # affine_params = (curr[0, 0], curr[0, 1], curr[0, 2], curr[1, 0], curr[1, 1], curr[1, 2])
            # transformed_image = self.pil_image.transform(
            #     (self.width, self.height),
            #     Image.AFFINE,
            #     affine_params,
            #     Image.BILINEAR
            # )

            # self.show_image(transformed_image)
            self.mat_affine = curr
            self.redraw_image()
            self.update()

            end = time.time()
            # print(end - start, 1/fps, end - start < 1 / fps)
            time.sleep(max(1 / fps - (end - start), 0))

        self.mat_affine = final_affine
    

class AnnotatedImage(ZoomableImage):
    def __init__(
            self,
            master=None,
            class_colors={},
            default_color='#00ff00',
            fill_intensity=50,
            add_category='drop',
            labeling_enabled=True,
            **kwargs
        ):
        self.annotations = []
        self.default_color = default_color
        self.class_colors = class_colors
        self.fill_intensity = fill_intensity
        self.add_category = add_category
        self._first_click = None
        self._last_click = None
        self.current_view = None
        self.show_annotations = True
        self.labeling_enabled = labeling_enabled
        super().__init__(master, **kwargs)

    def create_bindings(self):
        super().create_bindings()
        self.bind("<Double-Button-1>", self.toggle_annotations)
        if self.labeling_enabled:
            self.bind('<Button-3>', self.save_click)
            self.bind('<B3-Motion>', self.show_new_annotation)
            self.bind('<ButtonRelease-3>', self.save_new_annotation)
        
    def reset_bindings(self):
        self.unbind('<Button-3>')
        self.unbind('<B3-Motion>')
        self.unbind('<ButtonRelease-3>')
        self.unbind('<Button-1>')
        self.unbind('<B1-Motion>')
        self.unbind('<ButtonRelease-1>')
        self.unbind('<MouseWheel>')
        self.unbind('<Double-Button-1>')
        self.unbind('<Motion>')
        self.unbind('<Button-2>')
        self.unbind('<B2-Motion>')
        self.unbind('<ButtonRelease-2>')
        self.configure(cursor="")
        self.create_bindings()

    def set_annotation_bindings(self):
        self.labeling_enabled = True
        self.bind('<Motion>', self.show_cursor_axes)
        self.unbind('<Button-1>')
        self.unbind('<B1-Motion>')
        self.unbind('<ButtonRelease-1>')
        self.bind('<Button-1>', self.save_click)
        self.bind('<B1-Motion>', self.show_new_annotation)
        self.bind('<ButtonRelease-1>', self.save_new_annotation)
        self.configure(cursor="tcross")

    def set_class_colors(self, class_colors, default_color=None):
        self.class_colors = class_colors
        if default_color is not None:
            self.default_color = default_color

    def on_annotation_hover(self, event):
        annot = event.widget.annotation
        if annot is None:
            return
        
        dst = self.current_view
        if dst is None:
            dst = self.get_image_transformed(self.pil_image)
            overlay = self.create_annotations_overlay()
        else:
            overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        
        overlay = annot.draw(overlay, color='#ff00ff', affine=self.mat_affine)
        dst = Image.alpha_composite(dst.convert('RGBA'), overlay)

        self.show_image(dst)


    def show_cursor_axes(self, event):
        if self.pil_image is None:
            return
        
        dst = self.current_view
        # if dst is None:
        #     dst = self.get_image_transformed(self.pil_image)
        #     overlay = self.create_annotations_overlay()
        # else:
        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))

        draw = ImageDraw.Draw(overlay)
        draw.line([(0, event.y), (self.width, event.y)], fill='#ffffff40', width=2)
        draw.line([(event.x, 0), (event.x, self.height)], fill='#ffffff40', width=2)

        dst = Image.alpha_composite(dst.convert('RGBA'), overlay)

        self.show_image(dst)

    def save_click(self, event):
        self._first_click = event
        self.configure(cursor="tcross")

    def show_new_annotation(self, event):
        if self.pil_image is None:
            return
        
        dst = self.current_view
        # if dst is None:
        #     dst = self.get_image_transformed(self.pil_image)
        #     overlay = self.create_annotations_overlay()
        # else:
        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))

        x1 = min(self._first_click.x, event.x)
        y1 = min(self._first_click.y, event.y)
        x2 = max(self._first_click.x, event.x)
        y2 = max(self._first_click.y, event.y)

        draw = ImageDraw.Draw(overlay)
        draw.line([(0, event.y), (self.width, event.y)], fill='#ffffff40', width=2)
        draw.line([(event.x, 0), (event.x, self.height)], fill='#ffffff40', width=2)
        draw.rectangle((x1, y1, x2, y2), outline=self.class_colors[self.add_category], width=2)

        dst = Image.alpha_composite(dst.convert('RGBA'), overlay)

        self.show_image(dst)

    def save_new_annotation(self, event):
        x1 = min(self._first_click.x, event.x)
        y1 = min(self._first_click.y, event.y)
        x2 = max(self._first_click.x, event.x)
        y2 = max(self._first_click.y, event.y)

        x1, y1 = self.to_image_point(x1, y1)
        x2, y2 = self.to_image_point(x2, y2)
        annot = Annotation((x1, y1, x2, y2), self.add_category, false_negative=True)
        # self.annotations_listbox.insert(annot)
        self.annotations.append(annot)
        self.reset_bindings()
        self.redraw_image()
        self.event_generate("<<AnnotationFinished>>")
        

    def update_annotations(self, annotations):
        self.annotations = annotations
        self.redraw_image()

    def create_annotations_overlay(self):
        if self.pil_image is None:
            return

        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        for ix, annot in enumerate(self.annotations):
            if not annot.visible:
                continue
            layer = annot.draw(
                canvas_size=(self.width, self.height),
                fill_intensity=self.fill_intensity,
                color=self.class_colors.get(annot.category, self.default_color),
                affine=self.mat_affine,
                scale=self.current_scale/self.min_scale,
                text=str(ix + 1)
            )
            overlay = Image.alpha_composite(overlay, layer)
        
        return overlay
            
    def draw_image(self, pil_image):
        if pil_image is None:
            return
        
        self.pil_image = pil_image
        dst = self.get_image_transformed(self.pil_image)

        if len(self.annotations) > 0 and self.show_annotations:
            overlay = self.create_annotations_overlay()
            dst = Image.alpha_composite(dst.convert('RGBA'), overlay)

        self.current_view = dst
        self.show_image()

    def toggle_annotations(self, event=None):
        self.show_annotations = not self.show_annotations
        self.redraw_image()

    def make_animation(self, final_affine, initial_affine=None, duration='auto', fps=10):
        super().make_animation(final_affine, initial_affine, duration, fps)
   
    #     if initial_affine is None:
    #         initial_affine = self.mat_affine

    #     total_frames = int(duration * fps)
    #     delta_affine = (final_affine - initial_affine) / total_frames
    #     overlay = self.create_annotations_overlay()

    #     self.show_image(Image.alpha_composite(self.current_view.convert('RGBA'), overlay))

    #     for frame_number in range(total_frames + 1):
    #         start = time.time()
    #         curr = initial_affine + delta_affine * frame_number
    #         affine_params = (curr[0, 0], curr[0, 1], curr[0, 2], curr[1, 0], curr[1, 1], curr[1, 2])
    #         transformed_image = self.pil_image.transform(
    #             (self.width, self.height),
    #             Image.AFFINE,
    #             affine_params,
    #             Image.BILINEAR
    #         )

    #         self.show_image(transformed_image)
    #         self.update()

    #         time.sleep(max(1 / fps - (time.time() - start), 0))

        