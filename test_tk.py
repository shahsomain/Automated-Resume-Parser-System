from tkinter import Tk, filedialog

root = Tk()
root.withdraw()

file_path = filedialog.askopenfilename(
    title="Select a file", filetypes=[("All files", "*.*")]
)

print("Selected:", file_path if file_path else "No file selected")
