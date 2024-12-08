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
        self.categories = [
            'Revenus',
            'Maison',
            'Alimentation',
            'Transport',
            'Sortie',
            'Santé',
            'NC',
            'Interne']
        self.operations = pd.DataFrame(
            columns=["date", "name", "account", "amount", "category", "Mensuel"]
        )
        self.operations
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

    def add_operation(self, date, label, account, amount, category, monthly):
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
            "Mensuel": monthly
        }
        self.operations = pd.concat([self.operations, pd.DataFrame([new_op])], ignore_index=True)
        #self.operations.set_index('date', inplace=True)

    def import_operations_from_excel(self, file_path, gui_instance, mapping=None):
        """
        Import operations from an Excel or CSV file and assign them to the correct account.
        If the account number is not recognized, allow the user to associate it with an existing account,
        create a new account, or cancel the import.
        """
        # Detect file type
        file_extension = file_path.split(".")[-1].lower()

        # Load the file into a DataFrame
        if file_extension.startswith("xls"):
            df = pd.read_excel(file_path, skiprows=self._detect_header_row(file_path))
        elif file_extension == "csv":
            df = pd.read_csv(file_path, skiprows=self._detect_header_row(file_path))
        else:
            raise ValueError("Unsupported file type. Only Excel and CSV files are supported.")

        # Handle recognized formats
        newdf = None
        account_name = None
        for bank in DICTBANK:
            if DICTBANK[bank]['date'] in df:
                if bank == 'BoursoBank':
                    nbaccount = df['accountNum'][0]
                    accdf = pd.DataFrame({"date": df['dateOp'], "balance": df['accountbalance']})
                elif bank == 'BNP':
                    firstline = pd.read_excel(file_path, header=None, nrows=1)
                    nbaccount = firstline.values[0, 2]
                    accdf = pd.DataFrame({"date": [df[DICTBANK[bank]['date']].iloc[-1]], "balance": [firstline.values[0, 5]]})

                # Check if account number exists
                for account in self.accounts:
                    if nbaccount == self.accounts[account]["account_num"]:
                        account_name = account
                        break

                # If account is not found
                if account_name is None:
                    account_name = gui_instance.handle_unrecognized_account(nbaccount, accdf)
                    gui_instance.update_all()

                # Update account balance
                self.accounts[account_name]["account_balance"] = pd.concat(
                    [self.accounts[account_name]["account_balance"], accdf], ignore_index=True
                )

                # Build operations DataFrame
                newdf = pd.DataFrame(
                    {
                        "date": pd.to_datetime(df[DICTBANK[bank]['date']]),
                        "name": df[DICTBANK[bank]['name']],
                        "account": account_name,
                        "amount": pd.to_numeric(
                            df[DICTBANK[bank]['amount']]
                            .replace(",", ".", regex=True)  # Remplace les virgules par des points
                            .replace(r"\s", "", regex=True),  # Supprime les espaces éventuels
                            errors="coerce"  # Ignore les erreurs si certaines valeurs sont invalides
                        ),
                        "category": "NC",
                        "Mensuel": False,
                    }
                )
                break

        if newdf is None:
            if mapping:
                # Apply manual column mapping
                newdf = pd.DataFrame(
                    {
                        "date": df[mapping["date"]],
                        "name": df[mapping["name"]],
                        "amount": df[mapping["amount"]],
                        "account": account_name,
                        "Catégorie": "NC",
                        "Mensuel": False,
                    }
                )
            else:
                raise ValueError("Unrecognized file format. Mapping required.")
        if newdf.empty:
            raise ValueError("No data loaded.")
        # Add the new operations to the main DataFrame
        if self.operations.empty:
            self.operations = newdf
        else:
            self.operations = pd.concat([self.operations, newdf], ignore_index=True)
        gui_instance.update_all()

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
        Works for both Excel and CSV files.
        """
        file_extension = file_path.split(".")[-1].lower()

        if file_extension.startswith("xls"):  # Handle Excel files
            # Use pandas to inspect the first few rows
            df_preview = pd.read_excel(file_path, header=None, nrows=10)
            for i, row in df_preview.iterrows():
                if any(
                    DICTBANK[bank]["date"] in str(cell)
                    for bank in DICTBANK
                    for cell in row
                ):
                    return i
        elif file_extension == "csv":  # Handle CSV files
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    for i, line in enumerate(file):
                        if any(
                            DICTBANK[bank]["date"] in line
                            for bank in DICTBANK
                        ):
                            return i
            except UnicodeDecodeError:
                pass

        return 0  # Default to the first row if no header is found

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
        Set up the main graphical user interface components, including account management,
        filters for year/month, operations table, and visualization menu.
        """
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # Zone des comptes avec bouton "Add Account"
        accounts_frame = ttk.Frame(frame)
        accounts_frame.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        ttk.Label(accounts_frame, text="Accounts:").pack(side=tk.LEFT)
        add_account_button = ttk.Button(accounts_frame, text="+", width=2, command=self.add_account)
        add_account_button.pack(side=tk.LEFT, padx=5)
        add_account_button.bind("<Enter>", lambda e: self.show_tooltip(add_account_button, "Add new account"))
        add_account_button.bind("<Leave>", lambda e: self.hide_tooltip())

        self.accounts_listbox = tk.Listbox(frame, height=6, width=40)
        self.accounts_listbox.grid(row=1, column=0, rowspan=1, sticky=tk.NSEW, padx=5, pady=5)

        # Menus déroulants pour année et mois
        ttk.Label(frame, text="Year:").grid(row=2, column=0, padx=5, pady=5)
        self.year_var = tk.StringVar(value="All")
        self.year_menu = ttk.Combobox(frame, textvariable=self.year_var, state="readonly")
        self.year_menu.grid(row=3, column=0, padx=5, pady=5)
        self.year_menu.bind("<<ComboboxSelected>>", self.update_month_menu)

        ttk.Label(frame, text="Month:").grid(row=4, column=0, padx=5, pady=5)
        self.month_var = tk.StringVar(value="All")
        self.month_menu = ttk.Combobox(frame, textvariable=self.month_var, state="readonly")
        self.month_menu.grid(row=5, column=0, padx=5, pady=5)
        self.month_menu.bind("<<ComboboxSelected>>", self.update_operations_table)

        # Boutons de gestion des opérations
        ttk.Button(frame, text="Add Operation", command=self.add_operation).grid(row=6, column=0, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(frame, text="Import Operations", command=self.handle_import_operations).grid(row=7, column=0, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(frame, text="Categorize Operations", command=self.categorize_operations).grid(row=8, column=0, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(frame, text="Add Category", command=self.add_category).grid(row=9, column=0, sticky=tk.EW, padx=5, pady=2)
        # Boutons Modifier et Supprimer sous la table des opérations
        ttk.Button(frame, text="Edit Operation", command=self.edit_operation).grid(row=12, column=1, sticky=tk.EW, padx=5, pady=2)
        ttk.Button(frame, text="Delete Operation", command=self.delete_operation).grid(row=13, column=1, sticky=tk.EW, padx=5, pady=2)

        # Menu des visualisations
        visualize_frame = ttk.LabelFrame(frame, text="Visualize")
        visualize_frame.grid(row=10, column=0, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(visualize_frame, text="Account Balances", command=self.visualize_account_balances).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(visualize_frame, text="Spending by Category", command=self.visualize_category_spending).pack(fill=tk.X, padx=5, pady=2)

        # Bouton de sauvegarde des données
        ttk.Button(frame, text="Save Data", command=self.save_data).grid(row=11, column=0, sticky=tk.EW, padx=5, pady=2)

        # Table des opérations
        self.operations_table = ttk.Treeview(frame, columns=("date", "name", "account", "amount", "category", "Mensuel"), show="headings", height=20)
        self.operations_table.grid(row=0, column=1, rowspan=12, sticky=tk.NSEW, padx=5, pady=5)
        for col in self.operations_table["columns"]:
            self.operations_table.heading(col, text=col)
        # Configuration de la disposition
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        # Initialisation des données
        self.update_all()
        
    def update_all(self):
        self.update_accounts_list()
        self.update_year_menu()
        self.update_month_menu()
        self.update_operations_table()#can be removed

    def update_year_menu(self):
        """
        Updates the year dropdown with unique years from the operations.
        """
        if self.manager.operations.empty:
            self.year_menu["values"] = ["All"]
            self.year_var.set("All")
            return
        years = self.manager.operations["date"].dt.year.dropna().unique()
        years = sorted(years.astype(str).tolist())
        self.year_menu["values"] = ["All"] + years
        self.year_var.set("All")  # Default to all years
        
    def update_month_menu(self, event=None):
        """
        Updates the month dropdown based on the selected year.
        """
        if self.manager.operations.empty or self.year_var.get() == "All":
            self.month_menu["values"] = ["All"]
            self.month_var.set("All")
            return
        selected_year = self.year_var.get()
        months = self.manager.operations[self.manager.operations["date"].dt.year == int(selected_year)]["date"].dt.month
        months = sorted(months.dropna().unique().astype(str).tolist())
        self.month_menu["values"] = ["All"] + months
        self.month_var.set("All")
        self.update_operations_table()

    def show_tooltip(self, widget, text):
        """
        Display a tooltip with the specified text near the given widget.
        """
        x, y, _, _ = widget.bbox("insert")
        x += widget.winfo_rootx() + 20
        y += widget.winfo_rooty() + 20
        self.tooltip = tk.Toplevel(widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(self.tooltip, text=text, background="yellow", relief="solid", borderwidth=1)
        label.pack()

    def hide_tooltip(self):
        """
        Hide the currently displayed tooltip.
        """
        if hasattr(self, "tooltip"):
            self.tooltip.destroy()
            del self.tooltip

    def update_accounts_list(self):
        """
        Updates the list of accounts displayed in the listbox with their balances.
        """
        self.accounts_listbox.delete(0, tk.END)
        for account_name, details in self.manager.accounts.items():
            balance = details["account_balance"].iloc[-1] if not details["account_balance"].empty else 0
            self.accounts_listbox.insert(tk.END, f"{account_name} - {balance.iloc[-1]:.2f}€")

    def update_operations_table(self, event=None):
        """
        Updates the operations table based on the selected year and month.
        """
        # Filtrage par année
        filtered_operations = self.manager.operations
        selected_year = self.year_var.get()
        if selected_year != "All":
            filtered_operations = filtered_operations[filtered_operations["date"].dt.year == int(selected_year)]

            # Filtrage par mois
            selected_month = self.month_var.get()
            if selected_month != "All":
                filtered_operations = filtered_operations[filtered_operations["date"].dt.month == int(selected_month)]

        # Actualiser la table des opérations
        for row in self.operations_table.get_children():
            self.operations_table.delete(row)

        for idx, operation in filtered_operations.iterrows():
            self.operations_table.insert("", "end", values=operation.to_list())  # Utilise uniquement les colonnes

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

            try:
                # Add the operation
                self.manager.add_operation(date, label, account, amount, category, monthly)

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

        ttk.Button(add_window, text="Add", command=save_operation).grid(row=7, column=0, columnspan=2, pady=10)

    def delete_operation(self):
        """
        Deletes the selected operation from the table and the underlying data.
        """
        selected_item = self.operations_table.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select an operation to delete.")
            return

        # Get index of the selected operation in the DataFrame
        index = int(self.operations_table.item(selected_item)["values"][0])  # Assume first column is the DataFrame index

        # Confirm deletion
        confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this operation?")
        if confirm:
            self.manager.operations.drop(index, inplace=True)
            self.manager.operations.reset_index(drop=True, inplace=True)
            self.update_operations_table()
            messagebox.showinfo("Success", "Operation deleted successfully.")

    def edit_operation(self):
        """
        Opens a dialog to edit the selected operation.
        """
        selected_item = self.operations_table.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select an operation to edit.")
            return

        # Get index of the selected operation in the DataFrame
        index = int(self.operations_table.item(selected_item)["values"][0])  # Assume first column is the DataFrame index
        operation = self.manager.operations.loc[index]

        def save_changes():
            try:
                # Update the DataFrame with new values
                self.manager.operations.at[index, "date"] = pd.Timestamp(entry_date.get())
                self.manager.operations.at[index, "name"] = entry_name.get()
                self.manager.operations.at[index, "amount"] = float(entry_amount.get())
                self.manager.operations.at[index, "category"] = entry_category.get()
                self.manager.operations.at[index, "Mensuel"] = bool(monthly_var.get())

                self.update_operations_table()
                edit_window.destroy()
                messagebox.showinfo("Success", "Operation updated successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save changes: {e}")

        # Open edit dialog
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Operation")

        ttk.Label(edit_window, text="Date (YYYY-MM-DD):").grid(row=0, column=0, padx=5, pady=5)
        entry_date = ttk.Entry(edit_window)
        entry_date.insert(0, operation["date"])
        entry_date.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(edit_window, text="Name:").grid(row=1, column=0, padx=5, pady=5)
        entry_name = ttk.Entry(edit_window)
        entry_name.insert(0, operation["name"])
        entry_name.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(edit_window, text="Amount:").grid(row=2, column=0, padx=5, pady=5)
        entry_amount = ttk.Entry(edit_window)
        entry_amount.insert(0, operation["amount"])
        entry_amount.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(edit_window, text="Category:").grid(row=3, column=0, padx=5, pady=5)
        entry_category = ttk.Entry(edit_window)
        entry_category.insert(0, operation["category"])
        entry_category.grid(row=3, column=1, padx=5, pady=5)

        monthly_var = tk.IntVar(value=int(operation["Mensuel"]))
        ttk.Checkbutton(edit_window, text="Monthly", variable=monthly_var).grid(row=4, column=0, columnspan=2, padx=5, pady=5)

        ttk.Button(edit_window, text="Save", command=save_changes).grid(row=6, column=0, columnspan=2, pady=10)


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
            self.manager.import_operations_from_excel(file_path, self)
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
        file_path = filedialog.askopenfilename(filetypes=[("Excel and CSV files", "*.xls* *.csv")])

        if not file_path:
            return

        try:
            self.manager.import_operations_from_excel(file_path, self)
            messagebox.showinfo("Success", "Operations imported successfully.")
        except ValueError as e:
            # If a mapping error occurs, open the manual mapping interface
            if "Mapping required" in str(e):
                mapping = self.manual_column_mapping(pd.read_excel(file_path))
                if mapping:
                    self.manager.import_operations_from_excel(file_path, self, mapping=mapping)
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


    def handle_unrecognized_account(self, nbaccount, accdf):
        """
        Handles the case where the account number from the import file is not recognized.
        Opens a custom dialog with buttons for the user to choose an action:
        - Associate with an existing account
        - Create a new account
        - Cancel the import
        """
        def associate_with_existing_account():
            """
            Opens a dialog to let the user select an existing account.
            """
            def select_account():
                selected_account = account_var.get()
                if selected_account:
                    result["choice"] = "associate"
                    result["account_name"] = selected_account
                    dialog.destroy()

            account_var = tk.StringVar(value=list(self.manager.accounts.keys())[0] if self.manager.accounts else "")
            ttk.Label(dialog, text="Select an existing account:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
            account_menu = ttk.Combobox(dialog, textvariable=account_var, values=list(self.manager.accounts.keys()), state="readonly")
            account_menu.grid(row=1, column=1, padx=10, pady=10)
            ttk.Button(dialog, text="Select", command=select_account).grid(row=2, column=0, columnspan=2, pady=10)

        def create_new_account():
            """
            Opens a dialog to let the user create a new account.
            """
            def save_new_account():
                new_account_name = entry_name.get()
                if new_account_name:
                    self.manager.accounts[new_account_name] = {"account_num": nbaccount, "account_balance": accdf}
                    result["choice"] = "create"
                    result["account_name"] = new_account_name
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", "Account name is required.")

            ttk.Label(dialog, text="Enter a name for the new account:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
            entry_name = ttk.Entry(dialog)
            entry_name.grid(row=1, column=1, padx=10, pady=10)
            ttk.Button(dialog, text="Create", command=save_new_account).grid(row=2, column=0, columnspan=2, pady=10)

        def cancel_import():
            """
            Cancels the import process.
            """
            result["choice"] = "cancel"
            dialog.destroy()

        # Create the dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Unrecognized Account")
        ttk.Label(dialog, text=f"The account number {nbaccount} is not recognized.").grid(row=0, column=0, columnspan=3, padx=10, pady=10)
        
        # Buttons for actions
        if self.manager.accounts.keys():
            ttk.Button(dialog, text="Associate with Existing Account",
                   command=associate_with_existing_account).grid(row=3, column=0, padx=10, pady=10)
            rowcancel = 4
        else:
            rowcancel = 3
        
        ttk.Button(dialog, text="Create New Account",
                   command=create_new_account).grid(row=3, column=3, padx=10, pady=10)
        ttk.Button(dialog, text="Cancel Import",
                   command=cancel_import).grid(row=rowcancel, column=0, columnspan=2, pady=10)

        # Store the result and wait for user interaction
        result = {"choice": None, "account_name": None}
        self.root.wait_window(dialog)

        # Handle the result
        if result["choice"] in  ["associate", "create"]:
            return result["account_name"]
        elif result["choice"] == "cancel":
            raise ValueError("Import canceled by user.")
        else:
            raise ValueError("Unexpected error in account selection.")

    def open_virtual_operation_window(self):
        """
        Opens a window to create a virtual operation.
        """
        window = tk.Toplevel(self.root)
        window.title("Virtual Operation")

        tk.Label(window, text="From Category:").grid(row=0, column=0)
        from_category_var = tk.StringVar(value=self.manager.categories[0])
        from_category_menu = ttk.Combobox(window, textvariable=from_category_var, values=self.manager.categories)
        from_category_menu.grid(row=0, column=1)

        tk.Label(window, text="To Category:").grid(row=1, column=0)
        to_category_var = tk.StringVar(value=self.manager.categories[1])
        to_category_menu = ttk.Combobox(window, textvariable=to_category_var, values=self.manager.categories)
        to_category_menu.grid(row=1, column=1)

        tk.Label(window, text="Amount:").grid(row=2, column=0)
        amount_var = tk.DoubleVar()
        tk.Entry(window, textvariable=amount_var).grid(row=2, column=1)

        def add_virtual_op():
            try:
                self.manager.add_virtual_operation(from_category_var.get(), to_category_var.get(), amount_var.get())
                self.update_all()
                window.destroy()
            except ValueError as e:
                tk.messagebox.showerror("Error", str(e))

        tk.Button(window, text="Add", command=add_virtual_op).grid(row=3, column=0, columnspan=2)

    def update_category_balances(self):
        """
        Updates the display showing the balance of each category.
        """
        for widget in self.category_balance_frame.winfo_children():
            widget.destroy()

        for category in self.manager.categories:
            balance = self.manager.get_category_balance(category)
            tk.Label(self.category_balance_frame, text=f"{category}: {balance:.2f}€").pack(anchor="w")

    def update_category_summary(self):
        """
        Updates the category summary table with real, virtual, and total balances.
        """
        # Filtrer les opérations en fonction de l'année et du mois sélectionnés
        selected_year = self.year_var.get()
        selected_month = self.month_var.get()

        filtered_operations = self.manager.operations
        if selected_year != "All":
            filtered_operations = filtered_operations[filtered_operations["date"].dt.year == int(selected_year)]
            if selected_month != "All":
                filtered_operations = filtered_operations[filtered_operations["date"].dt.month == int(selected_month)]

        # Calculer les soldes par catégorie
        real_balances = filtered_operations[filtered_operations["account"] != "Virtual"].groupby("category")["amount"].sum()
        virtual_balances = filtered_operations[filtered_operations["account"] == "Virtual"].groupby("category")["amount"].sum()
        total_balances = self.manager.operations.groupby("category")["amount"].sum()

        # Insérer les lignes dans le tableau
        self.category_summary_table.delete(*self.category_summary_table.get_children())  # Clear existing rows
        self.category_summary_table.insert("", "end", values=[real_balances.get(cat, 0) for cat in self.manager.categories])
        self.category_summary_table.insert("", "end", values=[virtual_balances.get(cat, 0) for cat in self.manager.categories])
        self.category_summary_table.insert("", "end", values=[total_balances.get(cat, 0) for cat in self.manager.categories])


if __name__ == "__main__":
    try:
        manager = BudgetManager.load_from_file("budget_data.pkl")
    except FileNotFoundError:
        manager = BudgetManager()

    root = tk.Tk()
    gui = BudgetGUI(root, manager)
    root.mainloop()
