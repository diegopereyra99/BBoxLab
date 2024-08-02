import os
import customtkinter as ctk
from .objects.image import AnnotatedImage
from .objects.annotations import AnnotationListbox
import json
from threading import Lock

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class LabelingPage(ctk.CTkFrame):

    def __init__(self, master, dataset_folder, category_colors=None):
        super().__init__(master)
        
        # IMAGE FRAME
        relwidth = 0.85
        relheight = 0.9
        self.image_frame = ctk.CTkFrame(self, corner_radius=0)
        self.image_frame.place(relx=0.01, rely=0.02, relwidth=relwidth, relheight=relheight, anchor='nw')

        self.image_lbl = AnnotatedImage(self.image_frame, width=round(1280*relwidth), height=round(720*relheight))
        self.image_lbl.place(x=0, y=0, relwidth=1, relheight=1)

        # NAVIGATION FRAME
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0) # 400, 50
        self.navigation_frame.place(relx=0.01, rely=0.02 + relheight, relwidth=0.35, relheight=0.06, anchor='nw')

        self.slider = ctk.CTkSlider(self.navigation_frame, command=self.slider_changed)
        self.slider.place(relx=0.10, rely=0.5, relwidth=0.8, relheight=0.32, anchor='w')
        self.slider.set(0)

        self.next_button = ctk.CTkButton(self.navigation_frame, text=">", command=self.next_image)
        self.next_button.place(relx=0.98, rely=0.5, relwidth=0.07, relheight=0.7, anchor='e')

        self.prev_button = ctk.CTkButton(self.navigation_frame, text="<", command=self.prev_image)
        self.prev_button.place(relx=0.02, rely=0.5, relwidth=0.07, relheight=0.7, anchor='w')

        self.image_name_label = ctk.CTkLabel(self, text="", font=("Roboto", 16))
        self.image_name_label.place(relx=0.38, rely=0.06+relheight, anchor='w')

        # ANNOTATION FRAME
        self.annotation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.annotation_frame.place(relx=0.99, rely=0.02, relwidth=1-relwidth-0.03, relheight=relheight, anchor='ne')

        self.Label1 = ctk.CTkLabel(self.annotation_frame, fg_color="transparent", text="View")
        self.Label1.place(relx=0.02, y=0, relheight=0.03)

        self.checkboxes = {}
        chk_h = 0.04
        rely_chk = 0.04
        self.checkboxes['all'] = ctk.CTkCheckBox(self.annotation_frame, text="All") #, command=self.toggle_all)
        self.checkboxes['all'].place(relx=0.02, rely=rely_chk, relheight=chk_h)
        rely_chk += chk_h

        # self.categories = []

        # for category in self.categories:
        #     checkbox = ctk.CTkCheckBox(
        #         self.annotation_frame,
        #         fg_color=self.category_colors.get(category),
        #         checkmark_color='white',
        #         text=category.capitalize(),
        #     )
        #     checkbox.place(relx=0.02, relheight=chk_h, rely=rely_chk)
        #     self.checkboxes[category] = checkbox
        #     rely_chk += chk_h

        # self.checkboxes['fp'] = ctk.CTkCheckBox(self.annotation_frame, text="False positives")
        # self.checkboxes['fp'].place(relx=0.02, rely=0.08 + len(self.category_colors)*chk_h, relheight=chk_h)

        # self.checkboxes['fn'] = ctk.CTkCheckBox(self.annotation_frame, text="False negatives")
        # self.checkboxes['fn'].place(relx=0.02, rely=0.08 + len(self.category_colors)*chk_h + chk_h, relheight=chk_h)
        # rely_chk += chk_h*2
        
        self.Label2 = ctk.CTkLabel(self.annotation_frame, fg_color='transparent', text="Annotations")
        self.Label2.place(relx=0.02, rely=rely_chk+0.02, relheight=0.03)

        self.annotation_listbox = AnnotationListbox(self.annotation_frame)
        self.annotation_listbox.place(relx=0, rely=0.89, relwidth=1, relheight=0.89-rely_chk-0.05, anchor='sw')

        self.category_selector = ctk.CTkComboBox(self.annotation_frame, state='readonly', values=[], command=self.category_selector_changed)
        self.category_selector.place(relx=0, rely=0.94, relwidth=1, relheight=0.04, anchor='sw')

        self.add_button = ctk.CTkButton(self.annotation_frame, text="Add new", command=lambda: self.new_annotation(self.category_selector.get()))
        self.add_button.place(relx=0, rely=0.99, relwidth=1, relheight=0.04, anchor='sw')

        self.lock = Lock()

        self.category_colors = category_colors or {}
        self.images = []
        self.categories = []
        self.dataset_folder = None
        self.load_dataset(dataset_folder)

        # for name, checkbox in self.checkboxes.items():
        #     checkbox.configure(command=lambda name=name: self.checkbox_changed(name))
        self.create_bindings()
    
    @property
    def current_image(self):
        return self.images[self.current_index]
    
    @property
    def current_index(self):
        return round(self.slider.get())
    
    def on_resize(self, event=None):
        # TODO: Filter events that are not resize, because binding is <Configure> and function gets called many times.
        width = self.image_frame.winfo_width()
        height = self.image_frame.winfo_height()
        if width != self.image_lbl.width or height != self.image_lbl.height:
            self.image_lbl.resize_frame(width, height)
    
    def new_annotation(self, category):
        category = self.category_selector_changed(category)
        self.image_lbl.set_annotation_bindings()
        
    def category_selector_changed(self, category=None):
        if category is None:
            category = self.category_selector.get()
        self.image_lbl.add_category = category
        self.category_selector.set(category)
        return category
    
    def on_annotation_change(self, event=None):
        self.image_lbl.update_annotations(self.annotation_listbox.annotations)
        self.annotation_listbox.set_annotations(self.image_lbl.annotations)
        # self.autosave()

    def on_annotation_finish(self, event=None):
        # TODO: Fix to asjust to new format
        new_annot = self.image_lbl.annotations[-1]
        self.annotation_listbox.insert(new_annot)

        # self.autosave()

    def on_annotation_selected(self, event=None):
        annot = event.widget.annotation
        x = (annot.x1 + annot.x2) / 2
        y = (annot.y1 + annot.y2) / 2
        w_scale = self.image_lbl.pil_image.width / (annot.x2 - annot.x1)
        h_scale = self.image_lbl.pil_image.height / (annot.y2 - annot.y1)
        scale = min(w_scale, h_scale) * 3 / 4

        self.image_lbl.go_to_point(x, y, scale)

    def load_dataset(self, folder):
        if folder is None:
            return
        self.dataset_folder = folder
        self.images_folder = os.path.join(folder, 'images')
        self.predictions_folder = os.path.join(folder, 'predictions')
        with open(os.path.join(folder, 'classes.txt'), 'r') as f:
            self.categories = [name.strip() for name in f.readlines()]

        with open(os.path.join(folder, 'config.json'), 'r') as f:
            config = json.load(f)

        self.category_colors = config.get('category_colors', {})
        self.image_lbl.set_class_colors(self.category_colors)
        self.images = [fn for fn in os.listdir(self.images_folder) if fn.endswith(('.jpg', '.jpeg', '.png'))]

        # TODO: Add checkboxs for visibility according to classes
        self.annotation_listbox.categories = self.categories
        self.annotation_listbox.category_colors = self.category_colors

        # self.data.index.name = 'id'
        self.slider.configure(from_=0, to=len(self.images) - 1, number_of_steps=len(self.images)-1)
        self.slider.set(0)
        self.load_image(self.images[0]) # self.current_image
        # self.configure_checkboxes()

        self.category_selector.configure(values=self.categories)
        self.category_selector.set(self.categories[0])

    def load_image(self, image_fn):
        if self.lock.locked():
            return
        
        with self.lock:
            annots_fn = os.path.splitext(image_fn)[0] + '.txt'
            annots_path = os.path.join(self.predictions_folder, annots_fn)
            if os.path.exists(annots_path):
                self.annotation_listbox.load_annotations(annots_path, image_fn)
            else:
                self.annotation_listbox.delete("all")

            label = image_fn
            # if image is already labeled/corrected:
            #     label += " (corrected)"
            self.image_name_label.configure(text=label)
            self.image_lbl.set_image(os.path.join(self.images_folder, image_fn))
            self.image_lbl.update_annotations(self.annotation_listbox.annotations)

    def slider_changed(self, value):
        self.load_image(self.images[int(value)])

    def prev_image(self):
        current_index = self.current_index
        if current_index > 0:
            self.slider.set(current_index - 1)
            image = self.images[current_index - 1]
            self.load_image(image)

    def next_image(self):
        current_index = self.current_index
        if current_index < len(self.images) - 1:
            self.slider.set(current_index + 1)
            image = self.images[current_index + 1]
            self.load_image(image)

    # def configure_checkboxes(self):
    #     for name, checkbox in self.checkboxes.items():
    #         if name == 'all':
    #             pass
    #         if self.checkboxes['all'].get():
    #             checkbox.select()
    #         else:
    #             checkbox.deselect()

    # def checkbox_changed(self, name):
    #     # TODO: When a checkbox changes the state of the others should also be taken into account to update visibility
    #     if name == 'all':
    #         val = bool(self.checkboxes['all'].get())
    #         self.data['visible'] = val
    #         for name, checkbox in self.checkboxes.items():
    #             checkbox.select() if val else checkbox.deselect()
    #     else:
    #         visible = ~(self.data['visible'] * 0).astype(bool) # Set all to true
    #         visible[self.data['false_positive']] &= bool(self.checkboxes['fp'].get())
    #         visible[self.data['added']] &= bool(self.checkboxes['added'].get())
    #         visible[~(self.data['filtered']).astype(bool)] &= bool(self.checkboxes['filtered'].get())
    #         for cat in self.category_colors:
    #             visible[self.data['category'] == cat] &= bool(self.checkboxes[cat].get())
    #         self.data['visible'] = visible

    #     self.annotation_listbox.update_annotations_visibility()
    #     self.image_lbl.update_annotations(list(self.annotation_listbox.annotations.values()))


    def create_bindings(self):
        self.master.bind('<<AnnotationHover>>', self.image_lbl.on_annotation_hover)
        self.master.bind("<<AnnotationUnhover>>", lambda e: self.image_lbl.show_image())
        self.master.bind("<<AnnotationChanged>>", self.on_annotation_change)
        self.master.bind("<<AnnotationFinished>>", self.on_annotation_finish)
        self.master.bind("<<AnnotationSelected>>", self.on_annotation_selected)
        self.master.bind("d", lambda e: self.new_annotation('drop'))
        self.master.bind("e", lambda e: self.new_annotation('elevation'))
        self.master.bind("s", lambda e: self.new_annotation('spatter'))
        self.master.bind("t", lambda e: self.new_annotation('stripe'))
        self.master.bind("b", lambda e: self.new_annotation('bloat'))
        self.master.bind("<Configure>", self.on_resize)
        self.master.bind("<Left>", lambda e: self.prev_image())
        self.master.bind("<Right>", lambda e: self.next_image())
