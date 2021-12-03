import io
import ssl

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import tkinter as tk
import tkinter.tix as tix
import requests
from vm_key import *

from PIL import Image, ImageTk

# For more keys and their codes, see section 10 in this guide:
# https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf
# The one below is actually referred to as "Left GUI" not "WINDOWS"
HIDCODE.append(('KEY_WINDOWS', '0xe3', [('', [])]), )
HIDCODE.append(('KEY_UP', '0x52', [('', [])]), )
HIDCODE.append(('KEY_DOWN', '0x51', [('', [])]), )
HIDCODE.append(('KEY_LEFT', '0x50', [('', [])]), )
HIDCODE.append(('KEY_RIGHT', '0x4F', [('', [])]), )


def get_args():
    """
        Supports the command-line arguments listed below.
    """
    parser = argparse.ArgumentParser(
        description='Process args for retrieving all the Virtual Machines')
    parser.add_argument('-s', '--host', required=True, action='store',
                        help='Remote host to connect to')
    parser.add_argument('-o', '--port', type=int, default=443, action='store',
                        help='Port to connect on')
    parser.add_argument('-u', '--user', required=False, action='store',
                        help='User name to use when connecting to host')
    parser.add_argument('-p', '--password', required=False, action='store',
                        help='Password to use when connecting to host')
    #   parser.add_argument('-t', '--type', required=True, action='store',
    #                       help='Select Managed Object Type')
    parser.add_argument('-n', '--name', required=True, action='store',
                        help='Select Managed Object name')
    parser.add_argument('-w', '--writeto', required=False, action='store',
                        help='Write output to file')
    parser.add_argument('-m', '--revert_snaphot_name', required=False, action='store',
                        help='Name of the snapshot to revert to')
    parser.add_argument('-b', '--take_snaphot_name', required=False, action='store',
                        help='Name of the snapshot to take')
    parser.add_argument('-q', '--quiesce', default=False, action='store',
                        help='Enables quiesce guest file system when taking a snapshot (Needs VMware Tools installed)')

    args = parser.parse_args()
    return args


def get_all_objects(app):
    """
    Simple command-line program for listing the virtual machines on a system.
    """

    password = app.conf["ESXi/VCenter Password"].get()
    user_ = app.conf["ESXi/VCenter User"].get()
    host = app.conf["ESXi/VCenter IP"].get()

    context = None
    if hasattr(ssl, '_create_unverified_context'):
        context = ssl._create_unverified_context()
    si = SmartConnect(host=host,
                      user=user_,
                      pwd=password,
                      port=443,
                      sslContext=context)
    if not si:
        print("Could not connect to the specified host using specified "
              "username and password")
        return -1

    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    perf_manager = content.perfManager
    # create a mapping from performance stats to their counterIDs
    # counter_info: [performance stat => counterId]
    # performance stat example: cpu.usagemhz.LATEST
    # counterId example: 6
    counter_info = {}

    for c in perf_manager.perfCounter:
        # prefix = c.groupInfo.key TODO this is not used anymore
        full_name = str(
            c.key) + "." + c.groupInfo.key + "." + c.nameInfo.key + "." + c.rollupType + "." + c.unitInfo.label
        counter_info[full_name] = c.key
    # create a list of vim.VirtualMachine objects so
    # that we can query them for statistics
    # container = content.rootFolder
    container = content.rootFolder
    view_type = [vim.VirtualMachine, vim.ResourcePool, vim.HostSystem]
    recursive = True
    container_view = content.viewManager.CreateContainerView(container,
                                                             view_type,
                                                             recursive)
    children = container_view.view
    return children


def get_vms(app):
    all_obj = get_all_objects(app)
    return [objct for objct in all_obj if type(objct) == vim.VirtualMachine]


def make_app(app):
    app.vmlist = []

    app.columnconfigure(0, weight=0)
    app.columnconfigure(1, weight=1)
    app.rowconfigure(0, weight=0)
    app.rowconfigure(1, weight=0)
    app.rowconfigure(2, weight=0)
    app.rowconfigure(10, weight=1)

    app.conf_frame = tk.Frame(app)
    app.conf_frame.grid(row=0, column=1, padx=15, pady=5, sticky=tk.W)

    app.text_frame = tk.Frame(app)
    app.text_frame.grid(row=1, column=1, sticky=tk.EW)

    app.key_frame = tk.Frame(app)
    app.key_frame.grid(row=2, column=1, sticky=tk.EW)

    app.console_frame = tix.ScrolledWindow(app)
    app.console_frame.grid(row=10, column=1, sticky=tk.NSEW)

    app.vm_frame = tix.ScrolledWindow(app, width=250)
    tk.Label(app.vm_frame.window, text="Virtual Machines").pack(pady=10, side=tk.TOP, anchor=tk.N)
    tk.Button(app.vm_frame.window,
              text="Update Consoles",
              command=lambda a=app: toggle_vm_consoles(app)).pack(side=tk.TOP, anchor=tk.N)

    app.shrink_factor = tk.IntVar(value=1)
    app.columns = tk.IntVar(value=1)
    tk.Label(app.vm_frame.window, text="Console Shrink factor").pack(pady=10, side=tk.TOP, anchor=tk.N)
    tk.Radiobutton(app.vm_frame.window, text="/1", variable=app.shrink_factor, value=1).pack(side=tk.TOP, anchor=tk.N)
    tk.Radiobutton(app.vm_frame.window, text="/2", variable=app.shrink_factor, value=2).pack(side=tk.TOP, anchor=tk.N)
    tk.Radiobutton(app.vm_frame.window, text="/3", variable=app.shrink_factor, value=3).pack(side=tk.TOP, anchor=tk.N)
    tk.Label(app.vm_frame.window, text="Console grid columns").pack(pady=10, side=tk.TOP, anchor=tk.N)
    tk.Radiobutton(app.vm_frame.window, text="1", variable=app.columns, value=1).pack(side=tk.TOP, anchor=tk.N)
    tk.Radiobutton(app.vm_frame.window, text="2", variable=app.columns, value=2).pack(side=tk.TOP, anchor=tk.N)
    tk.Radiobutton(app.vm_frame.window, text="3", variable=app.columns, value=3).pack(side=tk.TOP, anchor=tk.N)

    app.vm_frame.grid(row=0, column=2, rowspan=11, padx=20, sticky=tk.NSEW)

    app.conf = {"ESXi/VCenter IP": tk.StringVar(),
                "ESXi/VCenter User": tk.StringVar(),
                "ESXi/VCenter Password": tk.StringVar()}

    for parm in app.conf:
        t = tix.LabelEntry(app.conf_frame, label=parm, labelside="top")
        t.entry["textvariable"] = app.conf[parm]
        t.entry["width"] = 20
        t.pack(side=tk.LEFT, padx=20)
        if "Pass" in parm:
            t.entry["show"] = "*"

    tix.Button(app.conf_frame, text="Connect", command=lambda x=app: populate_vms(x)).pack(side=tk.LEFT, padx=20)

    app.text = tix.ScrolledText(app.text_frame)
    app.text.text['height'] = 10
    app.text.pack(side=tk.LEFT, padx=15, pady=5, anchor=tk.W)

    tk.Button(app.text_frame,
              text="Send text to \n selected VMs",
              command=lambda a=app: send_text_to_selected_vms(a)).pack(side=tk.LEFT,
                                                                       padx=15,
                                                                       pady=5,
                                                                       expand=1,
                                                                       fill=tk.BOTH)

    key0_found = False
    button_row_len = 10
    button_row = 0
    button_col = 0
    for key_entry in HIDCODE:
        key = key_entry[0]
        if key == "KEY_0":
            key0_found = True
            continue

        if not key0_found:
            continue

        tix.Button(app.key_frame,
                   text=key.replace("KEY_", "", 1),
                   command=lambda a=app, x=key: send_key_to_selected_vms(a, x)).grid(row=button_row, column=button_col)
        button_col += 1
        if button_col >= button_row_len:
            button_row += 1
            button_col = 0


def populate_vms(app):
    vms = sorted(get_vms(app), key=lambda x: x.name)
    for vm in vms:
        check_button = tix.Checkbutton(app.vm_frame.window,
                                       text=vm.name)
        check_button["variable"] = check_button.var = tk.IntVar()
        if vm.runtime.powerState != "poweredOn":
            check_button["state"] = tk.DISABLED
            check_button["text"] += f" ({vm.runtime.powerState})"
        check_button.vm = vm
        check_button.console = {}
        app.vmlist.append(check_button)
        check_button.pack(side=tk.TOP, anchor=tk.W)


def toggle_vm_consoles(app):
    shrink_factor = app.shrink_factor.get()
    columns = app.columns.get()
    password = app.conf["ESXi/VCenter Password"].get()
    user = app.conf["ESXi/VCenter User"].get()
    host = app.conf["ESXi/VCenter IP"].get()
    top_level_url = f"https://{host}/"

    console_row = 0
    console_column = 0
    for old_console in app.console_frame.window.winfo_children():
        app.console_frame.after_cancel(old_console.refresh_job)
        old_console.destroy()
    for check_button in app.vmlist:
        vm = check_button.vm
        if vm.name in check_button.console:
            check_button.console[vm.name].pack_forget()
        if not check_button.var.get():
            continue
        url = top_level_url + f"screen?id={vm._moId}"
        content = requests.get(url, auth=(user, password), verify=False).content
        image = Image.open(io.BytesIO(content))
        image_width, image_height = image.size
        image = image.resize((int(image_width / shrink_factor), int(image_height / shrink_factor)), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(image)
        console = tk.Label(app.console_frame.window)
        tix.Balloon(app.console_frame).bind_widget(console, balloonmsg=vm.name)
        console.grid(row=console_row, column=console_column)
        check_button.console[vm.name] = console
        update_console(app.console_frame, console, img)
        console_column += 1
        if console_column >= columns:
            console_row += 1
            console_column = 0


def update_console(master, console, img):
    # Will it be a CPU issue if I don't stop updates?
    console["image"] = img
    console.refresh_job = master.after(1000, lambda m=master, c=console, i=img: update_console(m, c, i))


def send_key_to_selected_vms(app, key):
    for check_button in app.vmlist:
        vm = check_button.vm

        if check_button.var.get():
            key_stroke(vm, key_to_hid(key))


def send_text_to_selected_vms(app):
    text = app.text.text.get('1.0', tk.END)
    if text[-1] == "\n":
        text = text[:-1]
    if not text:
        return
    for check_button in app.vmlist:
        vm = check_button.vm

        if check_button.var.get():
            for chrctr in list(text):
                if chrctr == "\n":
                    key_stroke(vm, key_to_hid("KEY_ENTER"))
                elif chrctr == "\t":
                    key_stroke(vm, key_to_hid("KEY_TAB"))
                else:
                    key_stroke(vm, character_to_hid(chrctr))


def main():
    root = tix.Tk()
    root.title("I'm Brian and so's my wife")
    make_app(root)
    root.mainloop()


if __name__ == "__main__":
    main()
