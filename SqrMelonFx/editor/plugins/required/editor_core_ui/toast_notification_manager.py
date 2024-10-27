import gc
from pyqttoast import Toast, ToastPreset
from qt import QObject, QWidget

from editor_core_ui.style_manager import StyleManager


class ToastNotificationManager(QObject):

    def __init__(self, styleManager: StyleManager, parentWidget: QWidget, maxNotificationsOnScreen: int = 5) -> None:
        """
        Initialize the toast notification manager.
        Parameters:
            styleManager (StyleManager): The style manager to suscribe to changes.
            parentWidget (QWidget): The QWidget instance to contain the notifications.
            maxNotificationsOnScreen (int): Maximum notifications to display at once.
        """
        assert styleManager is not None
        assert parentWidget is not None

        super().__init__()

        Toast.setMaximumOnScreen(5)
        Toast.setPositionRelativeToWidget(parentWidget)
        self.__parentWidget = parentWidget
        self.__darkStyleEnabled = styleManager.darkStyle

        def styleChanged(emitter: StyleManager, darkStyleEnabled: bool, _) -> None:
            if emitter == styleManager:
                self.__darkStyleEnabled = darkStyleEnabled
        styleManager.styleChanged.connect(styleChanged)

    def displaySuccessToastNotification(self, title: str, message: str, durationMs: int = 4000) -> None: 
        """
        Display a temporary toast notification for success messages.
        Parameters:
            title: Notification title.
            message: Notification body.
            durationMs: Milliseconds the notification will be displayed on screen.
        """
        toastPreset = ToastPreset.SUCCESS_DARK if self.__darkStyleEnabled else ToastPreset.SUCCESS
        self.__displayToastNotification(title, message, durationMs, toastPreset)

    def displayInformationToastNotification(self, title: str, message: str, durationMs: int = 4000) -> None:
        """
        Display a temporary toast notification for informational messages.
        Parameters:
            title: Notification title.
            message: Notification body.
            durationMs: Milliseconds the notification will be displayed on screen.
        """
        toastPreset = ToastPreset.INFORMATION_DARK if self.__darkStyleEnabled else ToastPreset.INFORMATION
        self.__displayToastNotification(title, message, durationMs, toastPreset)

    def displayWarningToastNotification(self, title: str, message: str, durationMs: int = 4000) -> None:
        """
        Display a temporary toast notification for warning messages.
        Parameters:
            title: Notification title.
            message: Notification body.
            durationMs: Milliseconds the notification will be displayed on screen.
        """
        toastPreset = ToastPreset.WARNING_DARK if self.__darkStyleEnabled else ToastPreset.WARNING
        self.__displayToastNotification(title, message, durationMs, toastPreset)

    def displayErrorToastNotification(self, title: str, message: str, durationMs: int = 8000) -> None: 
        """
        Display a temporary toast notification for error messages.
        Parameters:
            title: Notification title.
            message: Notification body.
            durationMs: Milliseconds the notification will be displayed on screen.
        """
        toastPreset = ToastPreset.ERROR_DARK if self.__darkStyleEnabled else ToastPreset.ERROR
        self.__displayToastNotification(title, message, durationMs, toastPreset)

    def __displayToastNotification(self, title: str, message: str, durationMs: int, preset: ToastPreset) -> None:
        """
        Display a temporary toast notification.
        Parameters:
            title: Notification title.
            message: Notification body.
            durationMs: Duration for the notification, in milliseconds.
            preset: Notification visual preset to use.
        """

        toast = Toast(self.__parentWidget)
        toast.setMinimumWidth(250)
        toast.setTitle (title)
        toast.setText(message)
        toast.setBorderRadius(3)
        toast.applyPreset(preset)
        toast.setDuration(durationMs)
        toast.show()
