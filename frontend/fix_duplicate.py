import os, re, shutil
 
folder = os.path.dirname(os.path.abspath(__file__))
LINE = '<script src="budgetbuddy.js"></script>'
for name in sorted(os.listdir(folder)):
    if not name.lower().endswith(".html"):
        continue
    path = os.path.join(folder, name)
    text = original = open(path, encoding="utf-8").read()
    starts = [m.start() for m in re.finditer(r"<!DOCTYPE html>", text, flags=re.I)]
    notes = []
    if len(starts) > 1:
        text = text[starts[0]:starts[1]].rstrip() + "\n"
        notes.append(f"removed {len(starts) - 1} duplicate copy")
    if "budgetbuddy.js" not in text and "</body>" in text:
        i = text.rindex("</body>")
        text = text[:i] + "  " + LINE + "\n" + text[i:]
        notes.append("added the script line")
    if text != original:
        shutil.copy(path, path + ".bak")
        open(path, "w", encoding="utf-8").write(text)
    print(f"{name}: " + (", ".join(notes) if notes else "OK, nothing to change"))
