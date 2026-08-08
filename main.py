import os
import re
import shutil
import sqlite3
from kivy.app import App
from kivy.core.window import Window
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView
from kivy.graphics import Color, Rectangle, RoundedRectangle

# ==================== 全局中文字体注册 ====================
def init_chinese_font():
    font_paths = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-SC.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            LabelBase.register(DEFAULT_FONT, path)
            return

init_chinese_font()

# 移动端预览设计分辨率
Window.size = (400, 720)

CATEGORIES = ["河鲜海鲜", "酒水饮料", "冷菜", "热炒", "烧烤串串", "蒸菜"]

# ==================== 自定义美化控件 ====================

# 支持圆角与背景色的容器
class ColoredBoxLayout(BoxLayout):
    def __init__(self, bg_color=(1, 1, 1, 1), radius=0, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.radius = radius
        with self.canvas.before:
            Color(*self.bg_color)
            if self.radius > 0:
                self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
            else:
                self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

# 现代圆角立体感按钮
class RoundedButton(Button):
    def __init__(self, bg_color=(0.145, 0.388, 0.922, 1), radius=12, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.radius = radius
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.background_down = ''
        
        with self.canvas.before:
            self.shadow_color = Color(0, 0, 0, 0.15)
            self.shadow_rect = RoundedRectangle(pos=(self.x, self.y - 2), size=(self.width, self.height), radius=[self.radius])
            self.color_instruction = Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
            
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, instance, value):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.shadow_rect.pos = (self.x, self.y - 2)
        self.shadow_rect.size = self.size

# ==================== 路径与数据库初始化 ====================
def get_app_dir():
    return os.path.dirname(os.path.abspath(__file__))

def get_db_path():
    return os.path.join(get_app_dir(), "dishes.db")

def get_image_dir():
    img_dir = os.path.join(get_app_dir(), "images")
    if not os.path.exists(img_dir):
        os.makedirs(img_dir)
    return img_dir

def init_db():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            image_path TEXT
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM dishes")
    if cursor.fetchone()[0] == 0:
        sample_dishes = [
            ("清蒸鲈鱼", 68.0, "河鲜海鲜", ""),
            ("冰镇啤酒", 8.0, "酒水饮料", ""),
            ("凉拌黄瓜", 16.0, "冷菜", ""),
            ("宫保鸡丁", 38.0, "热炒", ""),
            ("羊肉串", 5.0, "烧烤串串", ""),
            ("农家蒸肉", 48.0, "蒸菜", "")
        ]
        cursor.executemany("INSERT INTO dishes (name, price, category, image_path) VALUES (?, ?, ?, ?)", sample_dishes)
        conn.commit()
    conn.close()

def parse_price_from_filename(file_path):
    if not file_path:
        return None
    base_name = os.path.basename(file_path)
    matches = re.findall(r'\d+(?:\.\d+)?', base_name)
    if matches:
        valid_numbers = [m for m in matches if len(m) < 7]
        return float(valid_numbers[-1]) if valid_numbers else float(matches[0])
    return None

def show_toast(title, text):
    content = ColoredBoxLayout(orientation='vertical', padding=20, spacing=15, bg_color=(0.95, 0.95, 0.97, 1), radius=16)
    content.add_widget(Label(text=text, halign="center", color=(0.2, 0.2, 0.2, 1), font_size='15sp'))
    btn = RoundedButton(text="确定", size_hint=(1, 0.4), bg_color=(0.145, 0.388, 0.922, 1), radius=10)
    popup = Popup(title=title, content=content, size_hint=(0.75, 0.3), background='')
    btn.bind(on_press=popup.dismiss)
    content.add_widget(btn)
    popup.open()

# ==================== 核心页面逻辑 ====================

# 1. 首页 (MainScreen)
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', spacing=20, padding=30)
        
        header = BoxLayout(orientation='vertical', size_hint_y=0.35, spacing=8)
        header.add_widget(Label(text="智慧餐饮系统", font_size='26sp', bold=True, color=(0.15, 0.15, 0.15, 1)))
        header.add_widget(Label(text="Smart Dining Mobile App", font_size='13sp', color=(0.5, 0.5, 0.5, 1)))
        layout.add_widget(header)

        # 移除可能引起方块报错的 Emoji
        btn_order = RoundedButton(text="在线点菜", font_size='18sp', size_hint_y=0.15,
                                  bg_color=(0.063, 0.725, 0.506, 1), radius=14)
        btn_order.bind(on_press=self.go_order)
        layout.add_widget(btn_order)

        btn_admin = RoundedButton(text="后台管理", font_size='18sp', size_hint_y=0.15,
                                  bg_color=(0.145, 0.388, 0.922, 1), radius=14)
        btn_admin.bind(on_press=self.go_admin)
        layout.add_widget(btn_admin)

        btn_exit = RoundedButton(text="退出应用", font_size='18sp', size_hint_y=0.15,
                                 bg_color=(0.75, 0.75, 0.78, 1), radius=14)
        btn_exit.bind(on_press=lambda x: App.get_running_app().stop())
        layout.add_widget(btn_exit)

        layout.add_widget(Label(text="v2.6 Modern Kivy Edition", font_size='11sp', color=(0.6, 0.6, 0.6, 1), size_hint_y=0.1))
        self.add_widget(layout)

    def go_order(self, instance):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = 'order'

    def go_admin(self, instance):
        self.manager.transition = SlideTransition(direction="left")
        self.manager.get_screen('admin').load_all_dishes()
        self.manager.current = 'admin'

# 2. 点菜主界面 (OrderScreen)
class OrderScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active_category = CATEGORIES[0]
        
        main_layout = BoxLayout(orientation='vertical')

        top_bar = ColoredBoxLayout(size_hint_y=0.08, bg_color=(0.145, 0.388, 0.922, 1), radius=0)
        btn_back = Button(text="< 返回", size_hint_x=0.25, background_color=(0,0,0,0), bold=True, font_size='14sp')
        btn_back.bind(on_press=self.go_back)
        lbl_title = Label(text="美食点餐", bold=True, font_size='18sp')
        top_bar.add_widget(btn_back)
        top_bar.add_widget(lbl_title)
        top_bar.add_widget(Label(size_hint_x=0.25))
        main_layout.add_widget(top_bar)

        content_box = BoxLayout(orientation='horizontal', size_hint_y=0.82)
        
        sidebar_scroll = ScrollView(size_hint_x=0.3)
        self.sidebar_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=6, padding=6)
        self.sidebar_layout.bind(minimum_height=self.sidebar_layout.setter('height'))
        
        self.cat_buttons = {}
        for cat in CATEGORIES:
            btn = RoundedButton(text=cat, size_hint_y=None, height=55, font_size='13sp', radius=10)
            btn.bind(on_press=lambda b, c=cat: self.switch_category(c))
            self.sidebar_layout.add_widget(btn)
            self.cat_buttons[cat] = btn
            
        sidebar_scroll.add_widget(self.sidebar_layout)
        content_box.add_widget(sidebar_scroll)

        dish_scroll = ScrollView(size_hint_x=0.7)
        self.dish_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10, padding=8)
        self.dish_layout.bind(minimum_height=self.dish_layout.setter('height'))
        dish_scroll.add_widget(self.dish_layout)
        content_box.add_widget(dish_scroll)

        main_layout.add_widget(content_box)

        bottom_bar = ColoredBoxLayout(size_hint_y=0.1, bg_color=(0.96, 0.96, 0.98, 1), padding=8, spacing=10)
        self.lbl_cart_status = Label(text="已选 0 份 | 合计: ¥0.00", bold=True, color=(1, 0.42, 0, 1), font_size='15sp')
        btn_checkout = RoundedButton(text="去结算 >", size_hint_x=0.4, bg_color=(1, 0.45, 0.1, 1), bold=True, radius=12, font_size='15sp')
        btn_checkout.bind(on_press=self.go_cart)
        bottom_bar.add_widget(self.lbl_cart_status)
        bottom_bar.add_widget(btn_checkout)
        main_layout.add_widget(bottom_bar)

        self.add_widget(main_layout)

    def on_enter(self):
        self.switch_category(self.active_category)
        self.update_cart_bar()

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = 'main'

    def switch_category(self, category):
        self.active_category = category
        for cat, btn in self.cat_buttons.items():
            if cat == category:
                btn.bg_color = (0.145, 0.388, 0.922, 1)
            else:
                btn.bg_color = (0.65, 0.65, 0.68, 1)

        self.dish_layout.clear_widgets()
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT name, price, image_path FROM dishes WHERE category = ?", (category,))
        dishes = cursor.fetchall()
        conn.close()

        for name, price, img_path in dishes:
            # 增大卡片高度以契合更大的字体
            card = ColoredBoxLayout(orientation='horizontal', size_hint_y=None, height=95, padding=6, spacing=8, bg_color=(1, 1, 1, 1), radius=12)
            
            full_img_path = os.path.abspath(os.path.join(get_app_dir(), img_path)) if img_path else ""
            if full_img_path and os.path.exists(full_img_path):
                img = AsyncImage(source=full_img_path, size_hint_x=0.35, allow_stretch=True, keep_ratio=True)
            else:
                img = Label(text="[无图]", size_hint_x=0.35, font_size='12sp', color=(0.6, 0.6, 0.6, 1))
            card.add_widget(img)

            info_box = BoxLayout(orientation='vertical', size_hint_x=0.35, spacing=6)
            info_box.add_widget(Label(text=name, bold=True, font_size='16sp', color=(0.2, 0.2, 0.2, 1), halign='left'))
            info_box.add_widget(Label(text=f"¥{price:.2f}", color=(1, 0.42, 0, 1), font_size='15sp', bold=True))
            card.add_widget(info_box)

            btn_add = RoundedButton(text="+ 选购", size_hint_x=0.3, bg_color=(0.063, 0.725, 0.506, 1), radius=10, font_size='14sp')
            btn_add.bind(on_press=lambda b, n=name, p=price, i=img_path: self.add_to_cart(n, p, i))
            card.add_widget(btn_add)

            self.dish_layout.add_widget(card)

    def add_to_cart(self, name, price, img_path):
        app = App.get_running_app()
        if name in app.cart:
            app.cart[name]['count'] += 1
        else:
            app.cart[name] = {'price': price, 'count': 1, 'image_path': img_path}
        self.update_cart_bar()

    def update_cart_bar(self):
        app = App.get_running_app()
        total_count = sum(item['count'] for item in app.cart.values())
        total_price = sum(item['price'] * item['count'] for item in app.cart.values())
        self.lbl_cart_status.text = f"已选 {total_count} 份 | 合计: ¥{total_price:.2f}"

    def go_cart(self, instance):
        app = App.get_running_app()
        if not app.cart:
            show_toast("提示", "购物车空空如也~")
            return
        self.manager.transition = SlideTransition(direction="left")
        self.manager.get_screen('cart').render_cart()
        self.manager.current = 'cart'

# 3. 购物车/确认订单 (CartScreen)
class CartScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        main_layout = BoxLayout(orientation='vertical')

        top_bar = ColoredBoxLayout(size_hint_y=0.08, bg_color=(0.145, 0.388, 0.922, 1), radius=0)
        btn_back = Button(text="< 返回", size_hint_x=0.25, background_color=(0,0,0,0), bold=True, font_size='14sp')
        btn_back.bind(on_press=self.go_back)
        top_bar.add_widget(btn_back)
        top_bar.add_widget(Label(text="确认订单", bold=True, font_size='18sp'))
        top_bar.add_widget(Label(size_hint_x=0.25))
        main_layout.add_widget(top_bar)

        scroll = ScrollView(size_hint_y=0.82)
        self.cart_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=8, padding=10)
        self.cart_layout.bind(minimum_height=self.cart_layout.setter('height'))
        scroll.add_widget(self.cart_layout)
        main_layout.add_widget(scroll)

        bottom_bar = ColoredBoxLayout(size_hint_y=0.1, bg_color=(0.96, 0.96, 0.98, 1), padding=8, spacing=10)
        self.lbl_total = Label(text="合计: ¥0.00", bold=True, color=(1, 0.42, 0, 1), font_size='16sp')
        btn_confirm = RoundedButton(text="确认下单", size_hint_x=0.4, bg_color=(0.063, 0.725, 0.506, 1), bold=True, radius=12, font_size='15sp')
        btn_confirm.bind(on_press=self.confirm_order)
        bottom_bar.add_widget(self.lbl_total)
        bottom_bar.add_widget(btn_confirm)
        main_layout.add_widget(bottom_bar)

        self.add_widget(main_layout)

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = 'order'

    def render_cart(self):
        self.cart_layout.clear_widgets()
        app = App.get_running_app()
        total = 0.0

        for name, info in list(app.cart.items()):
            subtotal = info['price'] * info['count']
            total += subtotal

            # 购物车单行卡片，增加高度容纳图片及更大字体
            item_box = ColoredBoxLayout(orientation='horizontal', size_hint_y=None, height=80, spacing=8, padding=6, bg_color=(1, 1, 1, 1), radius=10)
            
            # 增加菜品图片显示
            img_path = info.get('image_path', '')
            full_img_path = os.path.abspath(os.path.join(get_app_dir(), img_path)) if img_path else ""
            if full_img_path and os.path.exists(full_img_path):
                img = AsyncImage(source=full_img_path, size_hint_x=0.22, allow_stretch=True, keep_ratio=True)
            else:
                img = Label(text="[无图]", size_hint_x=0.22, font_size='11sp', color=(0.6, 0.6, 0.6, 1))
            item_box.add_widget(img)

            # 调整主文字信息占比，字体增大
            info_label = Label(text=f"{name}\n¥{info['price']:.2f} × {info['count']} = ¥{subtotal:.2f}",
                               font_size='13sp', size_hint_x=0.38, color=(0.2, 0.2, 0.2, 1), bold=True)
            item_box.add_widget(info_label)

            # 缩小加减删按钮的宽度占比，避免占用过多空间
            btn_minus = RoundedButton(text="-", size_hint_x=0.11, bg_color=(0.7, 0.7, 0.74, 1), radius=6, font_size='16sp')
            btn_minus.bind(on_press=lambda b, n=name: self.update_qty(n, -1))
            item_box.add_widget(btn_minus)

            btn_plus = RoundedButton(text="+", size_hint_x=0.11, bg_color=(0.145, 0.388, 0.922, 1), radius=6, font_size='16sp')
            btn_plus.bind(on_press=lambda b, n=name: self.update_qty(n, 1))
            item_box.add_widget(btn_plus)

            btn_del = RoundedButton(text="删", size_hint_x=0.18, bg_color=(0.9, 0.25, 0.25, 1), radius=6, font_size='13sp')
            btn_del.bind(on_press=lambda b, n=name: self.delete_item(n))
            item_box.add_widget(btn_del)

            self.cart_layout.add_widget(item_box)

        self.lbl_total.text = f"合计: ¥{total:.2f}"

    def update_qty(self, name, delta):
        app = App.get_running_app()
        if name in app.cart:
            app.cart[name]['count'] += delta
            if app.cart[name]['count'] <= 0:
                del app.cart[name]
        self.render_cart()

    def delete_item(self, name):
        app = App.get_running_app()
        if name in app.cart:
            del app.cart[name]
        self.render_cart()

    def confirm_order(self, instance):
        app = App.get_running_app()
        if not app.cart:
            show_toast("提示", "订单内无菜品")
            return
        
        total = sum(i['price'] * i['count'] for i in app.cart.values())
        show_toast("下单成功", f"订单已提交！\n应付总额: ¥{total:.2f}")
        app.cart.clear()
        self.go_back(None)

# 4. 后台管理界面 (AdminScreen)
class AdminScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_img_path = ""

        main_layout = BoxLayout(orientation='vertical')

        top_bar = ColoredBoxLayout(size_hint_y=0.08, bg_color=(0.145, 0.388, 0.922, 1), radius=0)
        btn_back = Button(text="< 返回", size_hint_x=0.25, background_color=(0,0,0,0), bold=True, font_size='14sp')
        btn_back.bind(on_press=self.go_back)
        top_bar.add_widget(btn_back)
        top_bar.add_widget(Label(text="后台管理", bold=True, font_size='18sp'))
        top_bar.add_widget(Label(size_hint_x=0.25))
        main_layout.add_widget(top_bar)

        add_panel = GridLayout(cols=2, size_hint_y=0.35, padding=12, spacing=8)
        
        add_panel.add_widget(Label(text="分类:", font_size='14sp', color=(0.2, 0.2, 0.2, 1), bold=True))
        self.spinner_cat = Spinner(text=CATEGORIES[0], values=CATEGORIES, font_size='14sp')
        add_panel.add_widget(self.spinner_cat)

        add_panel.add_widget(Label(text="菜名:", font_size='14sp', color=(0.2, 0.2, 0.2, 1), bold=True))
        self.input_name = TextInput(multiline=False, font_size='14sp')
        add_panel.add_widget(self.input_name)

        add_panel.add_widget(Label(text="价格:", font_size='14sp', color=(0.2, 0.2, 0.2, 1), bold=True))
        self.input_price = TextInput(multiline=False, input_filter='float', font_size='14sp')
        add_panel.add_widget(self.input_price)

        btn_img = RoundedButton(text="选择图片", bg_color=(0.7, 0.7, 0.74, 1), radius=8, font_size='13sp')
        btn_img.bind(on_press=self.open_file_chooser)
        self.lbl_img_status = Label(text="未选择", font_size='12sp', color=(0.5, 0.5, 0.5, 1))
        add_panel.add_widget(btn_img)
        add_panel.add_widget(self.lbl_img_status)

        btn_save = RoundedButton(text="保存菜品", bg_color=(0.063, 0.725, 0.506, 1), radius=10, font_size='15sp')
        btn_save.bind(on_press=self.save_dish)
        add_panel.add_widget(Label())
        add_panel.add_widget(btn_save)

        main_layout.add_widget(add_panel)

        scroll = ScrollView(size_hint_y=0.57)
        self.list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=6, padding=8)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll.add_widget(self.list_layout)
        main_layout.add_widget(scroll)

        self.add_widget(main_layout)

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = 'main'

    def open_file_chooser(self, instance):
        content = BoxLayout(orientation='vertical')
        file_chooser = FileChooserIconView(path=get_app_dir())
        content.add_widget(file_chooser)

        btn_box = BoxLayout(size_hint_y=0.15, spacing=10)
        btn_cancel = Button(text="取消", font_size='14sp')
        btn_select = RoundedButton(text="确定", bg_color=(0.145, 0.388, 0.922, 1), radius=8, font_size='14sp')
        btn_box.add_widget(btn_cancel)
        btn_box.add_widget(btn_select)
        content.add_widget(btn_box)

        popup = Popup(title="选择图片", content=content, size_hint=(0.9, 0.9))
        btn_cancel.bind(on_press=popup.dismiss)

        def select_file(inst):
            if file_chooser.selection:
                self.selected_img_path = file_chooser.selection[0]
                self.lbl_img_status.text = "已选择"
                auto_price = parse_price_from_filename(self.selected_img_path)
                if auto_price is not None:
                    self.input_price.text = str(auto_price)
            popup.dismiss()

        btn_select.bind(on_press=select_file)
        popup.open()

    def save_dish(self, instance):
        cat = self.spinner_cat.text
        name = self.input_name.text.strip()
        price_str = self.input_price.text.strip()

        if not name or not price_str or not self.selected_img_path:
            show_toast("提示", "请填写完整信息并选择图片")
            return

        price = float(price_str)
        dest_dir = get_image_dir()
        filename = f"{cat}_{os.path.basename(self.selected_img_path)}"
        dest_path = os.path.join(dest_dir, filename)
        
        shutil.copy(self.selected_img_path, dest_path)
        rel_img_path = os.path.relpath(dest_path, get_app_dir())

        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("INSERT INTO dishes (name, price, category, image_path) VALUES (?, ?, ?, ?)",
                       (name, price, cat, rel_img_path))
        conn.commit()
        conn.close()

        show_toast("成功", "菜品添加成功")
        self.input_name.text = ""
        self.input_price.text = ""
        self.selected_img_path = ""
        self.lbl_img_status.text = "未选择"
        self.load_all_dishes()

    def load_all_dishes(self):
        self.list_layout.clear_widgets()
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT id, category, name, price FROM dishes")
        rows = cursor.fetchall()
        conn.close()

        for dish_id, cat, name, price in rows:
            row_box = ColoredBoxLayout(orientation='horizontal', size_hint_y=None, height=52, spacing=6, padding=4, bg_color=(1, 1, 1, 1), radius=8)
            row_box.add_widget(Label(text=f"[{cat}] {name} - ¥{price:.2f}", font_size='13sp', size_hint_x=0.7, color=(0.2, 0.2, 0.2, 1), bold=True))
            
            btn_del = RoundedButton(text="删除", size_hint_x=0.3, bg_color=(0.9, 0.25, 0.25, 1), radius=6, font_size='13sp')
            btn_del.bind(on_press=lambda b, d_id=dish_id: self.delete_dish(d_id))
            row_box.add_widget(btn_del)

            self.list_layout.add_widget(row_box)

    def delete_dish(self, dish_id):
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dishes WHERE id = ?", (dish_id,))
        conn.commit()
        conn.close()
        self.load_all_dishes()

# ==================== 主程序入口 ====================
class DiningApp(App):
    def build(self):
        init_db()
        self.cart = {}
        
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(OrderScreen(name='order'))
        sm.add_widget(CartScreen(name='cart'))
        sm.add_widget(AdminScreen(name='admin'))
        return sm

if __name__ == '__main__':
    DiningApp().run()