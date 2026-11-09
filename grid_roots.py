"""Read-only window discovery policies shared by scanner and hit testing."""
SHELL_SURFACES={'Windows.UI.Core.CoreWindow','TopLevelWindowForOverflowXamlIsland',
                'NotifyIconOverflowWindow','XamlExplorerHostIslandWindow',
                'Xaml_WindowedPopupClass','ControlCenterWindow',
                'Microsoft.UI.Content.PopupWindowSiteBridge'}
SHELL_SURFACES.add('XamlExplorerHostIslandWindow_WASDK')


def popup_surface(kind):
    return interactive_shell(kind) or kind in ('Net UI Tool Window','#32768','ComboLBox')

def interactive_shell(kind):return kind in SHELL_SURFACES

def merge_roots(native,accessible):
    # UIA can omit native popups. Native enumeration can omit shell-band hosts.
    # Keep native z-order; add the otherwise undiscoverable shell surfaces above it.
    known={row['hwnd'] for row in native}
    extra=[]
    for row in accessible:
        if row['hwnd'] not in known:extra.append(row);known.add(row['hwnd'])
    return extra+native
