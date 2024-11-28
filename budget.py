import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import pickle
from typing import List
import matplotlib.pyplot as plt


DICTBANK = {
    'BNP':{
        "date": 'Date operation',
        "name": 'Libelle operation',
        "amount": 'Montant operation en euro'
        },
    'BoursoBank':{
        "date": 'dateOp',
        "name": 'label',
        "amount": 'amount'
        },
}

class BudgetManager:
    """
    Gère les comptes et les opérations budgétaires.
    Les opérations sont stockées dans un DataFrame avec les colonnes spécifiées.
    """
    
    def __init__(self, save_file: str = "budget_data.pkl"):
        self.accounts = {}
        self.categories = ['Revenus', 'Maison', 'Alimentation', 'Transport', 'Sortie', 'Santé', 'NC']
        self.operations = pd.DataFrame(
            columns=["date", "name", "account", "amount", "category", "Mensuel", "Interne"]
        )
        self.save_file = save_file

    def add_account(self, account_name, account_num, account_balance=None):
        """
        add acount if not existant
        """
        if account_name in self.accounts:
            raise ValueError(f"Le compte '{account_name}' existe déjà.")
        if account_balance is None:
            account_balance = pd.DataFrame({'date':pd.Timestamp.now(),'balance':0})
        self.accounts[account_name] = {'account_num':account_num,
                                       'account_balance':account_balance}

    def add_operation(self, date, label, account, amount, category, monthly, internal):
        """
        add operation to DataFrame
        """
        if account not in self.accounts:
            raise ValueError(f"Le compte '{account}' n'existe pas.")
        new_op = {
            "date": date,
            "name": label,
            "account": account,
            "amount": amount,
            "category": category,
            "Mensuel": monthly,
            "Interne": internal,
        }
        self.operations = pd.concat([self.operations, pd.DataFrame([new_op])], ignore_index=True)

    def import_operations_from_excel(self, file_path, account_name, mapping=None):
        """
        Import operations from an Excel or CSV file and assign them to the specified account.
        Filters out irrelevant lines before loading.
        Accepts manual column mappings if provided.
        """
        if account_name not in self.accounts:
            raise ValueError(f"The account '{account_name}' does not exist.")

        # Detect file type
        file_extension = file_path.split(".")[-1].lower()

        # Load the file into a DataFrame, attempting to filter out irrelevant lines
        if file_extension.startswith("xls"):
            df = pd.read_excel(file_path, skiprows=self._detect_header_row(file_path))
        elif file_extension == "csv":
            df = pd.read_csv(file_path, skiprows=self._detect_header_row(file_path))
        else:
            raise ValueError("Unsupported file type. Only Excel and CSV files are supported.")

        # Handle recognized formats
        newdf = None
        for bank in DICTBANK:
            if DICTBANK[bank]['date'] in df:  # BNP export
                newdf = pd.DataFrame(
                    {
                        "date": df[DICTBANK[bank]['date']],
                        "name": df[DICTBANK[bank]['name']],
                        "amount": df[DICTBANK[bank]['amount']],
                        "account": account_name,
                        "Catégorie": "NC",
                        "Mensuel": False,
                        "Interne": False,
                    }
                )
                if bank == 'BoursoBank':
                    accdf = pd.DataFrame(
                        {"date": df['dateOp'], "balance": df['accountbalance']}
                    )
                    self.accounts[account_name]["account_balance"] = pd.concat(
                        [self.accounts[account_name]["account_balance"], accdf], ignore_index=True
                    )
                break
        if newdf is None and mapping:
            # Apply manual column mapping if provided
            newdf = pd.DataFrame(
                {
                    "date": df[mapping["date"]],
                    "name": df[mapping["name"]],
                    "amount": df[mapping["amount"]],
                    "account": account_name,
                    "Catégorie": "NC",
                    "Mensuel": False,
                    "Interne": False,
                }
            )
        else:
            raise ValueError("Unrecognized file format. Mapping required.")

        # Add the new operations to the main DataFrame
        self.operations = pd.concat([self.operations, newdf], ignore_index=True)

    def save_to_file(self):
        """
        Sauvegarde les données dans un fichier pickle.
        """
        with open(self.save_file, 'wb') as file:
            pickle.dump(self, file)

    @staticmethod
    def load_from_file(file_path: str):
        """
        Charge les données depuis un fichier pickle.
        """
        with open(file_path, 'rb') as file:
            return pickle.load(file)

    def _detect_header_row(self, file_path):
        """
        Detects the row number where the header begins in an Excel or CSV file.
        Returns the row number to skip irrelevant lines at the top.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for i, line in enumerate(file):
                    for bank in DICTBANK:
                        if bank['date'] in line:  # Example heuristic for headers
                            return i
        except UnicodeDecodeError:  # Handle non-CSV (Excel-like) files
            pass

        return 0  # Default to the first row

class BudgetGUI:
    """
    GUI for the budget management system. Allows users to manage accounts and operations via a graphical interface.
    """

    def __init__(self, root: tk.Tk, manager: BudgetManager):
        """
        Initialize the GUI with the given root window and BudgetManager instance.
        """
        self.root = root
        self.manager = manager
        self.root.title("Budget Manager")
        self.root.geometry("900x600")
        self.setup_ui()

    def setup_ui(self):
        """
        Set up the main graphical user interface components.
        """
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Listbox for displaying accounts
        self.accounts_listbox = tk.Listbox(frame, height=10, width=40)
        self.accounts_listbox.grid(row=0, column=0, rowspan=6, sticky=tk.NSEW, padx=5, pady=5)

        # Buttons for managing accounts and operations
        ttk.Button(frame, text="Add Account", command=self.add_account).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(frame, text="Add Operation", command=self.add_operation).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(frame, text="Import Operations", command=self.import_operations).grid(row=2, column=1, sticky=tk.EW)
        ttk.Button(frame, text="View Operations", command=self.view_operations).grid(row=3, column=1, sticky=tk.EW)
        ttk.Button(frame, text="Save Data", command=self.save_data).grid(row=4, column=1, sticky=tk.EW)
        ttk.Button(frame, text="View Account Balances", command=self.view_account_balances).grid(row=5, column=1, sticky=tk.EW)
        ttk.Button(frame, text="Visualize Account Balances", command=self.visualize_account_balances).grid(row=6, column=1, sticky=tk.EW)
        ttk.Button(frame, text="Visualize Spending by Category", command=self.visualize_category_spending).grid(row=7, column=1, sticky=tk.EW)
        ttk.Button(frame, text="Categorize Operations", command=self.categorize_operations).grid(row=8, column=1, sticky=tk.EW)
        ttk.Button(frame, text="Add Category", command=self.add_category).grid(row=9, column=1, sticky=tk.EW)


        # Treeview table for displaying operations
        self.operations_table = ttk.Treeview(frame, columns=("date", "name", "account", "amount", "category", "Mensuel", "Interne"), show="headings", height=15)
        self.operations_table.grid(row=0, column=2, rowspan=6, sticky=tk.NSEW, padx=5, pady=5)
        for col in self.operations_table["columns"]:
            self.operations_table.heading(col, text=col)

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(2, weight=1)

        self.update_accounts_list()
        self.update_operations_table()

    def update_accounts_list(self):
        """
        Update the list of accounts displayed in the listbox.
        """
        self.accounts_listbox.delete(0, tk.END)
        for account_name in self.manager.accounts.keys():
            self.accounts_listbox.insert(tk.END, account_name)

    def update_operations_table(self):
        """
        Update the operations table with the current operations DataFrame.
        """
        for row in self.operations_table.get_children():
            self.operations_table.delete(row)
        for _, operation in self.manager.operations.iterrows():
            self.operations_table.insert("", "end", values=operation.to_list())

    def add_account(self):
        """
        Open a dialog for adding a new account. User provides account name, number, and optionally an initial balance.
        """
        def save_account():
            account_name = entry_name.get()
            account_num = entry_number.get()
            initial_balance = float(entry_balance.get()) if entry_balance.get() else 0.0

            try:
                balance_df = pd.DataFrame({pd.Timestamp.now(): [initial_balance]})
                self.manager.add_account(account_name, account_num, balance_df)
                self.update_accounts_list()
                add_window.destroy()
            except ValueError as e:
                messagebox.showerror("Error", str(e))

        add_window = tk.Toplevel(self.root)
        add_window.title("Add Account")

        ttk.Label(add_window, text="Account Name:").grid(row=0, column=0, padx=5, pady=5)
        entry_name = ttk.Entry(add_window)
        entry_name.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(add_window, text="Account Number:").grid(row=1, column=0, padx=5, pady=5)
        entry_number = ttk.Entry(add_window)
        entry_number.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(add_window, text="Initial Balance:").grid(row=2, column=0, padx=5, pady=5)
        entry_balance = ttk.Entry(add_window)
        entry_balance.grid(row=2, column=1, padx=5, pady=5)

        ttk.Button(add_window, text="Add", command=save_account).grid(row=3, column=0, columnspan=2, pady=10)

    def add_category(self):
        """
        Opens a dialog to add a new category to the list of categories.
        """
        def save_category():
            new_category = entry_category.get()
            if new_category and new_category not in self.manager.categories:
                self.manager.categories.append(new_category)
                messagebox.showinfo("Success", f"Category '{new_category}' added.")
                add_window.destroy()
            else:
                messagebox.showerror("Error", "Category already exists or is invalid.")

        add_window = tk.Toplevel(self.root)
        add_window.title("Add Category")

        ttk.Label(add_window, text="Category Name:").grid(row=0, column=0, padx=5, pady=5)
        entry_category = ttk.Entry(add_window)
        entry_category.grid(row=0, column=1, padx=5, pady=5)

        ttk.Button(add_window, text="Add", command=save_category).grid(row=1, column=0, columnspan=2, pady=10)

    def add_operation(self):
        """
        Open a dialog for adding a new operation manually and automatically update the account balance.
        """
        def save_operation():
            date = pd.Timestamp(entry_date.get())
            label = entry_label.get()
            account = account_var.get()
            amount = float(entry_amount.get())
            category = entry_category.get()
            monthly = bool(monthly_var.get())
            internal = bool(internal_var.get())

            try:
                # Add the operation
                self.manager.add_operation(date, label, account, amount, category, monthly, internal)

                # Update the account balance
                self.manager.accounts[account]['account_balance'].loc[date] = (
                    self.manager.accounts[account]['account_balance'].iloc[-1, 0] + amount
                )

                self.update_operations_table()
                add_window.destroy()
            except ValueError as e:
                messagebox.showerror("Error", str(e))

        add_window = tk.Toplevel(self.root)
        add_window.title("Add Operation")

        ttk.Label(add_window, text="Date (YYYY-MM-DD):").grid(row=0, column=0, padx=5, pady=5)
        entry_date = ttk.Entry(add_window)
        entry_date.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(add_window, text="Label:").grid(row=1, column=0, padx=5, pady=5)
        entry_label = ttk.Entry(add_window)
        entry_label.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(add_window, text="Account:").grid(row=2, column=0, padx=5, pady=5)
        account_var = tk.StringVar()
        account_menu = ttk.OptionMenu(add_window, account_var, *self.manager.accounts.keys())
        account_menu.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(add_window, text="Amount:").grid(row=3, column=0, padx=5, pady=5)
        entry_amount = ttk.Entry(add_window)
        entry_amount.grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(add_window, text="Category:").grid(row=4, column=0, padx=5, pady=5)
        entry_category = ttk.Entry(add_window)
        entry_category.grid(row=4, column=1, padx=5, pady=5)

        monthly_var = tk.IntVar()
        ttk.Checkbutton(add_window, text="Monthly", variable=monthly_var).grid(row=5, column=0, columnspan=2, padx=5, pady=5)

        internal_var = tk.IntVar()
        ttk.Checkbutton(add_window, text="Internal", variable=internal_var).grid(row=6, column=0, columnspan=2, padx=5, pady=5)

        ttk.Button(add_window, text="Add", command=save_operation).grid(row=7, column=0, columnspan=2, pady=10)

    def categorize_operations(self):
        """
        Opens a dialog to assign categories to operations that are not categorized or are categorized as 'NC'.
        """
        def save_and_next():
            # Save category for the current operation
            current_index = non_categorized_indices[op_index[0]]
            selected_category = category_var.get()
            self.manager.operations.at[current_index, "category"] = selected_category
            # Move to the next operation
            op_index[0] += 1
            if op_index[0] < len(non_categorized_indices):
                show_operation(op_index[0])
            else:
                messagebox.showinfo("Success", "All operations have been categorized.")
                self.update_operations_table()
                categorize_window.destroy()

        def show_operation(index):
            current_index = non_categorized_indices[index]
            operation = self.manager.operations.iloc[current_index]

            # Display operation details
            label_operation.config(text=f"{operation['date']} | {operation['name']} | {operation['amount']} €")

            # Set default category suggestion
            default_category = "NC"
            for keyword, category in categorization_rules.items():
                if keyword in operation["name"].upper():
                    default_category = category
                    break
            category_var.set(default_category)
            
        def add_category_in_catop(obj):
            obj.add_category()
            lastcat = obj.categories[-1]
            category_var.set(lastcat)
            category_menu['menu'].add_command(label=lastcat, command=tk._setit(category_var, lastcat))
            

        # Filter non-categorized operations
        non_categorized_indices = self.manager.operations[
            (self.manager.operations["category"] == "NC") | (self.manager.operations["category"].isnull())
        ].index.tolist()

        if not non_categorized_indices:
            messagebox.showinfo("Info", "No uncategorized operations found.")
            return

        # Categorization rules
        categorization_rules = {
            "SALAIRE": "Revenus",
            "BLABLACAR": "Transport",
            "AUTOROUTE": "Transport",
            "VIAL": "Alimentation",
            "ALIM": "Alimentation",
            "FREE MOBILE": "Maison",
            "SANTE": "Santé",
            "RESTO": "Sortie",
            "ESL": "Maison",
        }

        op_index = [0]  # Track current operation index

        # Create window for categorization
        categorize_window = tk.Toplevel(self.root)
        categorize_window.title("Categorize Operations")

        label_operation = ttk.Label(categorize_window, text="", font=("Arial", 12), wraplength=400)
        label_operation.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        category_var = tk.StringVar()
        ttk.Label(categorize_window, text="Category:").grid(row=1, column=0, padx=10, pady=5)
        category_menu = ttk.OptionMenu(categorize_window, category_var, *self.manager.categories)
        category_menu.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(categorize_window, text="Next", command=save_and_next).grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(categorize_window, text="Add Category", command=self.add_category).grid(row=3, column=0,columnspan=2, pady=10)

        # Show the first operation
        show_operation(0)

    def import_operations(self):
        """
        Allow the user to import operations from an Excel file for a specific account.
        """
        file_path = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xls*"),
                       ("csv files", "*.csv")])
        account_name = self.accounts_listbox.get(tk.ACTIVE)
        if not file_path or not account_name:
            return
        try:
            self.manager.import_operations_from_excel(file_path, account_name)
            self.update_operations_table()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def view_operations(self):
        """
        Display all operations in the table.
        """
        self.update_operations_table()

    def view_account_balances(self):
        """
        Display balances for all accounts in a separate dialog.
        """
        balances = "\n".join(
            f"{account}: {self.manager.accounts[account]['account_balance'].iloc[-1, 0]:.2f}€"
            for account in self.manager.accounts.keys()
        )
        messagebox.showinfo("Account Balances", balances)

    def save_data(self):
        """
        Save all data to a pickle file.
        """
        self.manager.save_to_file()
        messagebox.showinfo("Success", "Data saved successfully.")

    def visualize_account_balances(self):
        """
        Display a bar chart of account balances using matplotlib.
        """
        account_names = []
        balances = []

        for account, details in self.manager.accounts.items():
            account_names.append(account)
            balances.append(details['account_balance'].iloc[-1, 0])  # Latest balance

        plt.figure(figsize=(8, 6))
        plt.bar(account_names, balances, color='skyblue')
        plt.title("Account Balances")
        plt.xlabel("Accounts")
        plt.ylabel("Balance (€)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
        
    def visualize_category_spending(self):
        """
        Display a pie chart of spending per category using matplotlib.
        """
        spending = self.manager.operations.groupby("category")["amount"].sum()
        categories = spending.index
        amounts = spending.values

        plt.figure(figsize=(8, 6))
        plt.pie(amounts, labels=categories, autopct="%1.1f%%", startangle=140, colors=plt.cm.Paired.colors)
        plt.title("Spending by Category")
        plt.axis("equal")  # Ensure the pie chart is circular
        plt.tight_layout()
        plt.show()

    def handle_import_operations(self):
        """
        Handle importing operations from a file. Allows manual mapping of columns if needed.
        """
        file_path = filedialog.askopenfilename(filetypes=[("Excel and CSV files", "*.xlsx *.csv")])
        account_name = self.accounts_listbox.get(tk.ACTIVE)

        if not file_path or not account_name:
            return

        try:
            self.manager.import_operations_from_excel(file_path, account_name)
            messagebox.showinfo("Success", "Operations imported successfully.")
        except ValueError as e:
            # If a mapping error occurs, open the manual mapping interface
            if "Mapping required" in str(e):
                mapping = self.manual_column_mapping(pd.read_excel(file_path))
                if mapping:
                    self.manager.import_operations_from_excel(file_path, account_name, mapping=mapping)
                    messagebox.showinfo("Success", "Operations imported successfully with custom mapping.")
            else:
                messagebox.showerror("Error", str(e))
                
    def manual_column_mapping(self, df):
        """
        Opens a dialog to allow the user to map columns manually to the required format.
        Returns a dictionary with the column mappings or None if the user cancels.
        """
        def save_mapping():
            try:
                mapping_result["date"] = entry_date.get()
                mapping_result["name"] = entry_name.get()
                mapping_result["amount"] = entry_amount.get()
                mapping_window.destroy()
            except KeyError as e:
                messagebox.showerror("Error", f"Invalid mapping: {e}")

        def cancel_mapping():
            mapping_result.clear()
            mapping_window.destroy()

        mapping_window = tk.Toplevel(self.root)
        mapping_window.title("Map Columns")
        mapping_result = {}

        # Dropdown menus for each column
        ttk.Label(mapping_window, text="Date Column:").grid(row=0, column=0, padx=5, pady=5)
        entry_date = ttk.Combobox(mapping_window, values=df.columns.tolist())
        entry_date.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(mapping_window, text="Name Column:").grid(row=1, column=0, padx=5, pady=5)
        entry_name = ttk.Combobox(mapping_window, values=df.columns.tolist())
        entry_name.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(mapping_window, text="Amount Column:").grid(row=2, column=0, padx=5, pady=5)
        entry_amount = ttk.Combobox(mapping_window, values=df.columns.tolist())
        entry_amount.grid(row=2, column=1, padx=5, pady=5)

        # Save or cancel buttons
        ttk.Button(mapping_window, text="Save", command=save_mapping).grid(row=3, column=0, pady=10)
        ttk.Button(mapping_window, text="Cancel", command=cancel_mapping).grid(row=3, column=1, pady=10)

        # Wait for user input
        self.root.wait_window(mapping_window)
        return mapping_result if mapping_result else None


if __name__ == "__main__":
    try:
        manager = BudgetManager.load_from_file("budget_data.pkl")
    except FileNotFoundError:
        manager = BudgetManager()

    root = tk.Tk()
    gui = BudgetGUI(root, manager)
    root.mainloop()
