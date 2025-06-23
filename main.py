import os
import json
import random
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import StringProperty, NumericProperty, DictProperty, ObjectProperty, ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.lang import Builder
from kivy.uix.popup import Popup
from kivy.metrics import dp

# Custom widget for displaying a single product in the home screen's RecycleView.
class ProductCard(BoxLayout):
    images = ListProperty([])
    title = StringProperty('')
    description = StringProperty('')
    price = StringProperty('')
    quantity_in_cart = StringProperty('')
    callback = ObjectProperty(lambda: None)

    # Populates the horizontal image scroller when the images list is updated.
    def on_images(self, *args):
        image_grid = self.ids.image_grid
        image_grid.clear_widgets()
        for image_path in self.images:
            image = Image(source=image_path, size_hint=(None, 1), width=dp(200))
            image_grid.add_widget(image)

# Custom widget for displaying an item in the shopping cart's RecycleView.
class CartCard(BoxLayout):
    image = StringProperty('')
    title = StringProperty('')
    price = StringProperty('')
    delete_callback = ObjectProperty(lambda: None)

# The initial screen for user login.
class LoginScreen(Screen):
    # Handles user login, sets up the app state, and transitions to the home screen.
    def login_user(self):
        nickname = self.ids.nickname_input.text.strip()
        if nickname:
            app = App.get_running_app()
            app.nickname = nickname
            app.balance = 10000
            app.cart = {}
            app.root.current = 'home'

# The main screen displaying the list of products.
class HomeScreen(Screen):
    products_data = ListProperty([])

    # Refreshes user info and product list upon entering the screen.
    def on_enter(self, *args):
        self.update_user_info()
        self.load_products()

    # Updates the balance display.
    def update_user_info(self):
        app = App.get_running_app()
        self.ids.balance_label.text = f"BALANCE: ${app.balance}"

    # Loads products from the main app and formats them for the RecycleView.
    def load_products(self):
        app = App.get_running_app()
        if not app.items:
            app.load_all_items()

        # Sets a random deal of the day if one isn't already set.
        if not app.deal:
            app.deal = random.choice(app.items)

        self.products_data = []
        for item in app.items:
            qty = app.cart.get(item['title'], 0)
            self.products_data.append({
                'title': item['title'],
                'description': item['description'],
                'price': f"${item['price']}",
                'images': item['images'],
                'quantity_in_cart': f"In Cart: {qty}" if qty > 0 else "",
                'callback': lambda x=item: app.add_to_cart(x)
            })

# Screen for displaying and managing the shopping cart.
class CartScreen(Screen):
    cart_data = ListProperty([])
    subtotal = NumericProperty(0)

    # Reloads cart contents every time the screen is shown.
    def on_pre_enter(self):
        self.load_cart()

    # Loads items from the app's cart dictionary and prepares them for display.
    def load_cart(self):
        app = App.get_running_app()
        
        self.subtotal = 0
        self.cart_data = []

        for item_title, qty in app.cart.items():
            item_details = next((item for item in app.items if item['title'] == item_title), None)
            if item_details:
                self.subtotal += item_details['price'] * qty
                self.cart_data.append({
                    'title': f"{item_title} x{qty}",
                    'price': f"${item_details['price'] * qty}",
                    'image': item_details['images'][0] if item_details['images'] else 'assets/nothing_box.png',
                    'delete_callback': lambda x=item_title: app.remove_from_cart(x)
                })

# Screen for displaying user profile information.
class ProfileScreen(Screen):
    # Updates the balance when the screen is entered.
    def on_enter(self, *args):
        self.update_balance()

    # Updates the balance label with the current balance from the app.
    def update_balance(self):
        app = App.get_running_app()
        self.ids.profile_balance.text = f"Bank Balance:\n${app.balance}"

# Screen for displaying the "Deal of the Day".
class DealScreen(Screen):
    deal_img = StringProperty('')
    deal_title = StringProperty('')
    deal_price = StringProperty('')

    # Loads the current deal's information when the screen is entered.
    def on_enter(self, *args):
        app = App.get_running_app()
        deal = app.deal
        if deal:
            if deal['images']:
                self.deal_img = deal['images'][0]
            else:
                self.deal_img = 'assets/nothing_box.png'
            self.deal_title = deal.get('title', 'No deal today!')
            self.deal_price = f"DEAL PRICE: ${deal.get('price', 'N/A')}"
        else:
            self.deal_img = ''
            self.deal_title = 'No deal today!'
            self.deal_price = 'Come back tomorrow!'

# Main application class.
class MainApp(App):
    nickname = StringProperty("Guest")
    balance = NumericProperty(0)
    cart = DictProperty({})
    deal = ObjectProperty(None, rebind=True, allownone=True)
    items = []
    root: ScreenManager

    # Builds the app, loading UI from the .kv file.
    def build(self):
        self.load_all_items()
        return Builder.load_file("ui.kv")

    # Loads all item data from the JSON file into memory.
    def load_all_items(self):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        items_path = os.path.join(script_dir, 'items.json')
        with open(items_path) as f:
            self.items = json.load(f)

    # Adds an item to the shopping cart and refreshes the relevant screens.
    def add_to_cart(self, item):
        title = item['title']
        self.cart[title] = self.cart.get(title, 0) + 1
        self.root.get_screen('home').load_products()
        if self.root.current == 'cart':
            self.root.get_screen('cart').load_cart()

    # Removes an item from the shopping cart and refreshes screens.
    def remove_from_cart(self, item_title):
        if item_title in self.cart:
            del self.cart[item_title]
            self.root.get_screen('cart').load_cart()
            self.root.get_screen('home').load_products()

    # Adds the current deal item to the cart.
    def add_deal_to_cart(self):
        if self.deal:
            self.add_to_cart(self.deal)
            self.root.current = 'cart'

    # Processes the purchase, deducting cost from balance and clearing the cart.
    def buy_now(self):
        total_cost = 0
        for item_title, qty in self.cart.items():
            item_details = next((item for item in self.items if item['title'] == item_title), None)
            if item_details:
                total_cost += item_details['price'] * qty

        if self.balance >= total_cost:
            self.balance -= total_cost
            self.cart = {}
            # Update screens
            self.root.get_screen('cart').load_cart()
            if self.root.current == 'home':
                self.root.get_screen('home').update_user_info()
            if self.root.current == 'profile':
                 self.root.get_screen('profile').update_balance()
        else:
            # Shows a popup if the user has insufficient funds.
            popup = Popup(title='Insufficient Funds',
                          content=Label(text='You do not have enough money...'),
                          size_hint=(None, None), size=(400, 200))
            popup.open()
    
    # Resets the app state and returns to the login screen.
    def logout(self):
        self.nickname = "Guest"
        self.balance = 0
        self.cart = {}
        self.deal = {}
        self.root.current = 'login'

# Entry point for the application.
if __name__ == '__main__':
    MainApp().run()
