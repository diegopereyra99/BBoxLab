import customtkinter
from CTkListbox import CTkListbox
from PIL import Image, ImageDraw
import numpy as np
import tkinter as tk
from functools import wraps

class Annotation:
    def __init__(self, bbox, category, image_fn=None, id=None, confidence=None, visible=True, false_positive=False, false_negative=False):
        self.image_fn = image_fn
        self.bbox = bbox
        self.category = category
        self.id = id
        self.confidence = confidence
        self.visible = visible
        if false_positive and false_negative:
            raise ValueError("Can't mark an annotation as both false positive and false negative")
        self.false_positive = false_positive
        self.false_negative = false_negative

    def to_dict(self):
        return {
            "image_fn": self.image_fn,
            "x1": self.bbox[0],
            "y1": self.bbox[1],
            "x2": self.bbox[2],
            "y2": self.bbox[3],
            "category": self.category,
            "id": self.id,
            "confidence": self.confidence,
            "visible": self.visible,
            "false_positive": self.false_positive,
            "false_negative": self.false_negative,
        }

    @property
    def x1(self):
        return self.bbox[0]

    @property
    def y1(self):
        return self.bbox[1]

    @property
    def x2(self):
        return self.bbox[2]

    @property
    def y2(self):
        return self.bbox[3]
    
    @property
    def width(self):
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self):
        return self.bbox[3] - self.bbox[1]
    
    @property
    def xyxy(self):
        return self.bbox
    
    @property
    def xywh(self):
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2, self.width, self.height)

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def toggle(self):
        self.visible = not self.visible

    def set_false_positive(self):
        if self.false_negative:
            raise ValueError("Can't mark an added annotation as false positive")
        else:
            self.false_positive = True

    def draw(self, image=None, canvas_size=None, affine=None, scale=1, color="#00ff00", text=None, fill_intensity=50):
        if image is None and canvas_size is None:
            raise ValueError("Either 'image' or 'canvas_size' must be provided")
        elif image is None:
            overlay = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
        else:
            overlay = image.copy()

        draw_im = ImageDraw.Draw(overlay)
        x1, y1, x2, y2 = self.bbox

        if affine is not None:
            x1, y1, _ = affine @ np.array([x1, y1, 1])
            x2, y2, _ = affine @ np.array([x2, y2, 1])
            
        width_ = round((3 - scale)/2 + 1) if scale <= 3 else 1
        draw_im.rectangle((x1, y1, x2, y2), outline=color, width=width_, fill=f'{color}{fill_intensity:02X}')

        # If it is a false positive draw a red cross in upper right corner
        if self.false_negative:
            radius = 1 + round(scale) / 2
            draw_im.circle((x2, y1), radius, fill='black') 

        if self.false_positive:
            # Draw a cross in upper right corner
            size = 1 + round(scale) / 2
            draw_im.line((x2 - size, y1 - size, x2 + size, y1 + size), fill='red', width=2)
            draw_im.line((x2 - size, y1 + size, x2 + size, y1 - size), fill='red', width=2)

        if text is not None:
            size = 10 if scale <= 2 else 10 + round((scale - 2) * 2)
            draw_im.text((x1 - size/2, y1 - size/2), str(text), fill="white", align="center", font_size=size)

        return overlay


def annotation_update(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.event_generate("<<AnnotationChanged>>")
        return result
    return wrapper


class AnnotationButton(customtkinter.CTkButton):
    def __init__(self, annotation:Annotation, **kwargs):
        self.annotation = annotation
        self.id = annotation.id
        self.index = kwargs.pop('index')
        self.color = kwargs.get('fg_color', 'transparent')
        kwargs['fg_color'] = self.color if annotation.visible else 'transparent'
        if annotation.false_positive:
            kwargs['text_color'] = 'red'
        elif annotation.false_negative:
            kwargs['text_color'] = 'black'
        super().__init__(**kwargs)

    def _on_enter(self, event=None):
        super()._on_enter(event)
        self.event_generate("<<AnnotationHover>>")
        # highlight annotation on image

    def _on_leave(self, event=None):
        super()._on_leave(event)
        self.event_generate("<<AnnotationUnhover>>")
        # highlight annotation on image

    def hide(self, update=True):
        self.annotation.hide()
        self.configure(fg_color='transparent')
        if update:
            self.event_generate("<<AnnotationChanged>>")

    def show(self, update=True):
        self.annotation.show()
        self.configure(fg_color=self.color)
        if update:
            self.event_generate("<<AnnotationChanged>>")

    def go_to(self):
        self.event_generate("<<AnnotationSelected>>")
        if not self.annotation.visible:
            self.show()

    @annotation_update
    def set_false_positive(self):
        self.configure(text_color='red')
        self.annotation.set_false_positive()

    @annotation_update
    def unmark_false_positive(self):
        self.configure(text_color='white')
        self.annotation.false_positive = False

    def delete(self):
        self.master.delete(self.index)

    def _create_bindings(self):
        super()._create_bindings()
        self.bind("<Button-3>", self.menu_popup)

    def menu_popup(self, event=None):
        menu = tk.Menu(self, tearoff=0)
        if self.annotation.visible:
            menu.add_command(label="Hide", command=self.hide)
        else:
            menu.add_command(label="Show", command=self.show)
        
        if self.annotation.false_positive:
            menu.add_command(label="False positive (unmark)", command=self.unmark_false_positive)
        elif not self.annotation.false_negative:
            menu.add_command(label="False positive", command=self.set_false_positive)

        if self.annotation.false_negative:
            menu.add_command(label="Delete", command=self.delete)

        menu.add_command(label="Go to", command=self.go_to)
        
        if event is not None:
            menu.post(event.x_root, event.y_root)
        else:
            menu.post(self.winfo_rootx() + self.winfo_width(), self.winfo_rooty())

class AnnotationListbox(CTkListbox):
    def __init__(self, master, **kwargs):
        self.categories = kwargs.pop('categories', [])
        self.category_colors = kwargs.pop('category_colors', {})
        super().__init__(master, **kwargs)
        # self.annotations = {}
    
    def load_annotations(self, annotations_path, image_fn=None):
        annotations = []
        with open(annotations_path, 'r') as f:
            for line in f:
                cat, x, y, w, h, conf = [float(x) for x in line.strip().split(' ')]
                x1 = x - w / 2
                y1 = y - h / 2
                x2 = x + w / 2
                y2 = y + h / 2
                cat = self.categories[int(cat)] if int(cat) < len(self.categories) else int(cat)
                annot = Annotation((x1, y1, x2, y2), cat, image_fn=image_fn, confidence=conf)
                annotations.append(annot)

        self.set_annotations(annotations)

    def set_annotations(self, annotations):
        self.delete("all")
        for annot in annotations:
            self.insert(annot, update=False)
        self.update()

    @property
    def annotations(self):
        return [b.annotation for ix, b in self.buttons.items()]
    
    def insert(self, annot, index=None, text=None, color=None, update=True, **args):
        """add new option in the listbox"""

        if index is None:
            index = self.end_num 
            self.end_num += 1

        if text is None:
            text = f"{index + 1}: {annot.category}"
            if annot.confidence is not None:
                text += f" ({annot.confidence:.2f})"

        if color is None:
            fg_color = self.category_colors.get(annot.category, self.button_fg_color)
            border_color = self.category_colors.get(annot.category)

        # self.annotations[index] = annot
        # button = super().insert(index, text, **args)
        
        self.buttons[index] = AnnotationButton(
            annot,
            master=self,
            index=index,
            text=text,
            anchor=self.justify,
            text_color=self.text_color,
            font=self.font,
            hover_color=self.hover_color,
            fg_color=fg_color,
            border_color=border_color,
            border_width=1,
            **args,
        )
        self.buttons[index].configure(command=lambda num=index: self.buttons[index].go_to())
        
        if type(index) is int:
            self.buttons[index].grid(padx=0, pady=(0, 5), sticky="nsew", column=0, row=index)
        else:
            self.buttons[index].grid(padx=0, pady=(0, 5), sticky="nsew", column=0)
            
        if update:
            self.update()

        if self.multiple:
            self.buttons[index].bind(
                "<Shift-1>", lambda e: self.select_multiple(self.buttons[index])
            )

        return self.buttons[index]

    def toggle_selection(self, index):
        button = self.buttons[index]
        if button in self.selections or button == self.selected:
            self.deselect(index)
        else:
            self.select(index)

    def deselect(self, index=None):
        if not self.multiple:
            if self.selected:
                self.selected.configure(fg_color=self.selected.color)
                self.selected = None
            return
        if self.buttons[index] in self.selections:
            self.selections.remove(self.buttons[index])
            self.buttons[index].configure(fg_color=self.buttons[index].color)

    def select(self, index):
        """select the option"""
        
        if isinstance(index, int):
            if index in self.buttons:
                selected_button = self.buttons[index]
            else:
                selected_button = list(self.buttons.values())[index]
        else:
            selected_button = self.buttons[index]
  
        if self.multiple:
            if selected_button in self.selections:
                self.selections.remove(selected_button)
                selected_button.configure(fg_color=self.buttons[index].cget('fg_color'), hover=False)
                self.after(100, lambda: selected_button.configure(hover=self.hover))
            else:
                self.selections.append(selected_button)
            for i in self.selections:
                i.configure(fg_color=self.select_color, hover=False)
                self.after(100, lambda button=i: button.configure(hover=self.hover))
        else:
            self.selected = selected_button
            selected_button.configure(fg_color=self.select_color, hover=False)
            self.after(100, lambda: selected_button.configure(hover=self.hover))

        if self.command:
            self.command(self.get())


    def delete(self, index, last=None):
        """delete options from the listbox"""
        if str(index).lower() == "all":
            self.deactivate("all")
            for i in self.buttons:
                self.buttons[i].destroy()
            self.update()
            self.buttons = {}
            self.end_num = 0
            return

        if str(index).lower() == "end":
            self.end_num -= 1
            if len(self.buttons.keys())>0:
                index = list(self.buttons.keys())[-1]
            if index not in self.buttons:
                return
        else:
            if int(index) >= len(self.buttons):
                return
            if not last:
                index = list(self.buttons.keys())[int(index)]

        if last:
            if str(last).lower() == "end":
                last = len(self.buttons) - 1
            elif int(last) >= len(self.buttons):
                last = len(self.buttons) - 1

            deleted_list = []
            for i in range(int(index), int(last) + 1):
                list(self.buttons.values())[i].destroy()
                deleted_list.append(list(self.buttons.keys())[i])
                self.update()
            for i in deleted_list:
                del self.buttons[i]
        else:
            self.buttons[index].destroy()
            if self.multiple:
                if self.buttons[index] in self.selections:
                    self.selections.remove(self.buttons[index])
            del self.buttons[index]

        self.event_generate("<<AnnotationChanged>>")
