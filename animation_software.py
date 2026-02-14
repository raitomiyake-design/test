import sys
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QSlider, QLabel, 
                             QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
                             QGraphicsRectItem, QColorDialog, QFileDialog, QMessageBox,
                             QSpinBox, QComboBox, QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPen, QPainter, QFont


class AnimatedObject(QGraphicsEllipseItem):
    """Movable animated object with keyframe support"""
    def __init__(self, x, y, size=50):
        super().__init__(0, 0, size, size)
        self.setPos(x, y)
        self.base_color = QColor(100, 150, 255)
        self.setBrush(QBrush(self.base_color))
        self.setPen(QPen(Qt.black, 2))
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable, True)
        self.object_id = id(self)
        self.keyframes = {}  # {frame: {'x': x, 'y': y, 'brightness': brightness}}
        self.brightness = 100
        
    def add_keyframe(self, frame):
        """Add keyframe at current position and brightness"""
        self.keyframes[frame] = {
            'x': self.pos().x(),
            'y': self.pos().y(),
            'brightness': self.brightness
        }
        
    def remove_keyframe(self, frame):
        """Remove keyframe"""
        if frame in self.keyframes:
            del self.keyframes[frame]
            
    def get_interpolated_state(self, frame):
        """Get interpolated position and brightness for given frame"""
        if not self.keyframes:
            return None
            
        # If exact keyframe exists, return it
        if frame in self.keyframes:
            return self.keyframes[frame]
        
        # Find surrounding keyframes
        before_frames = [f for f in self.keyframes.keys() if f < frame]
        after_frames = [f for f in self.keyframes.keys() if f > frame]
        
        if not before_frames:
            # Before first keyframe
            first_frame = min(self.keyframes.keys())
            return self.keyframes[first_frame]
        
        if not after_frames:
            # After last keyframe
            last_frame = max(self.keyframes.keys())
            return self.keyframes[last_frame]
        
        # Interpolate between keyframes
        frame_before = max(before_frames)
        frame_after = min(after_frames)
        
        kf_before = self.keyframes[frame_before]
        kf_after = self.keyframes[frame_after]
        
        # Linear interpolation
        t = (frame - frame_before) / (frame_after - frame_before)
        
        return {
            'x': kf_before['x'] + (kf_after['x'] - kf_before['x']) * t,
            'y': kf_before['y'] + (kf_after['y'] - kf_before['y']) * t,
            'brightness': kf_before['brightness'] + (kf_after['brightness'] - kf_before['brightness']) * t
        }
        
    def set_brightness(self, brightness):
        """Set brightness (0-200, 100 is normal)"""
        self.brightness = brightness
        # Apply brightness to base color
        factor = brightness / 100.0
        new_color = QColor(
            min(255, int(self.base_color.red() * factor)),
            min(255, int(self.base_color.green() * factor)),
            min(255, int(self.base_color.blue() * factor))
        )
        self.setBrush(QBrush(new_color))
        
    def set_base_color(self, color):
        """Set the base color and reapply brightness"""
        self.base_color = color
        self.set_brightness(self.brightness)


class TimelineBar(QGraphicsRectItem):
    """Movable timeline bar"""
    def __init__(self, height, on_move_callback):
        super().__init__(0, 0, 2, height)
        self.setBrush(QBrush(QColor(255, 0, 0)))
        self.setPen(QPen(Qt.red, 2))
        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges, True)
        self.on_move_callback = on_move_callback
        self.setZValue(100)  # Always on top
        
    def itemChange(self, change, value):
        if change == QGraphicsRectItem.ItemPositionChange:
            # Restrict movement to horizontal only
            new_pos = value
            new_pos.setY(0)
            # Notify callback
            if self.on_move_callback:
                self.on_move_callback(new_pos.x())
            return new_pos
        return super().itemChange(change, value)


class Canvas(QGraphicsView):
    """Main canvas for animation"""
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setSceneRect(0, 0, 800, 600)
        self.setRenderHint(QPainter.Antialiasing)
        self.objects = []
        
    def add_object(self, obj_type='circle'):
        """Add new animated object"""
        if obj_type == 'circle':
            obj = AnimatedObject(400, 300)
        else:
            obj = AnimatedObject(400, 300)
        self.objects.append(obj)
        self.scene.addItem(obj)
        return obj
        
    def get_selected_object(self):
        """Get currently selected object"""
        selected = self.scene.selectedItems()
        for item in selected:
            if isinstance(item, AnimatedObject):
                return item
        return None
        
    def clear_all(self):
        """Clear all objects"""
        for obj in self.objects:
            self.scene.removeItem(obj)
        self.objects = []


class Timeline(QGraphicsView):
    """Timeline view with keyframes"""
    frame_changed = pyqtSignal(int)
    
    def __init__(self, max_frames=300):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.max_frames = max_frames
        self.frame_width = 10
        self.timeline_height = 100
        self.setSceneRect(0, 0, self.max_frames * self.frame_width, self.timeline_height)
        self.setFixedHeight(150)
        self.current_frame = 0
        self.objects = []
        
        # Set background
        self.setBackgroundBrush(QBrush(QColor(240, 240, 240)))
        
        # Create timeline bar
        self.timeline_bar = TimelineBar(self.timeline_height, self.on_bar_move)
        self.scene.addItem(self.timeline_bar)
        
        self.draw_timeline()
        
    def on_bar_move(self, x_pos):
        """Called when timeline bar is moved"""
        frame = int(x_pos / self.frame_width)
        frame = max(0, min(frame, self.max_frames - 1))
        self.current_frame = frame
        self.frame_changed.emit(frame)
        
    def draw_timeline(self):
        """Draw timeline grid"""
        # Clear previous timeline (except bar)
        for item in self.scene.items():
            if item != self.timeline_bar:
                self.scene.removeItem(item)
        
        # Draw background grid
        for i in range(0, self.max_frames):
            x = i * self.frame_width
            # Every 10th frame is darker
            if i % 10 == 0:
                line = self.scene.addLine(x, 0, x, self.timeline_height, 
                                         QPen(QColor(150, 150, 150), 2))
            else:
                line = self.scene.addLine(x, 0, x, self.timeline_height, 
                                         QPen(QColor(220, 220, 220), 1))
        
        # Draw frame numbers
        for i in range(0, self.max_frames, 10):
            x = i * self.frame_width
            text = self.scene.addText(str(i))
            text.setFont(QFont("Arial", 8))
            text.setPos(x + 2, -18)
            text.setDefaultTextColor(Qt.black)
            
        # Draw keyframe markers for all objects
        self.draw_keyframes()
        
    def draw_keyframes(self):
        """Draw keyframe markers for all objects"""
        if not self.objects:
            return
            
        row_height = self.timeline_height / max(1, len(self.objects))
        
        for idx, obj in enumerate(self.objects):
            y_pos = idx * row_height
            
            # Draw object indicator with label
            rect = self.scene.addRect(0, y_pos, 40, row_height - 2, 
                                     QPen(Qt.darkGray, 1), QBrush(obj.base_color))
            
            # Add object number
            text = self.scene.addText(f"Obj {idx+1}")
            text.setFont(QFont("Arial", 7))
            text.setPos(2, y_pos + row_height/2 - 8)
            text.setDefaultTextColor(Qt.white if obj.base_color.lightness() < 128 else Qt.black)
            
            # Draw keyframes
            for frame in obj.keyframes.keys():
                x = frame * self.frame_width
                keyframe_marker = self.scene.addEllipse(
                    x - 5, y_pos + row_height/2 - 5, 10, 10,
                    QPen(Qt.darkBlue, 2), QBrush(QColor(255, 220, 0))
                )
                keyframe_marker.setZValue(50)
                
    def set_frame(self, frame):
        """Set current frame and move bar"""
        self.current_frame = frame
        x = frame * self.frame_width
        self.timeline_bar.setPos(x, 0)
        
    def update_objects(self, objects):
        """Update list of objects to display keyframes for"""
        self.objects = objects
        self.draw_keyframes()


class AnimationSoftware(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Animation Software")
        self.setGeometry(100, 100, 1200, 800)
        
        self.current_frame = 0
        self.max_frames = 300
        self.is_playing = False
        self.fps = 30
        
        # Setup UI
        self.setup_ui()
        
        # Animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)
        
    def setup_ui(self):
        """Setup user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        
        # Title label
        title_label = QLabel("Animation Studio")
        title_font = QFont("Arial", 16, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("background-color: #2c3e50; color: white; padding: 10px; border-radius: 5px;")
        main_layout.addWidget(title_label)
        
        # Top controls in a group box
        control_group = QGroupBox("Object Controls")
        control_layout = QHBoxLayout()
        
        # Add object button
        self.add_btn = QPushButton("+ Add Object")
        self.add_btn.clicked.connect(self.add_object)
        self.add_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px; font-weight: bold;")
        control_layout.addWidget(self.add_btn)
        
        # Color button
        self.color_btn = QPushButton("Change Color")
        self.color_btn.clicked.connect(self.change_color)
        self.color_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px; font-weight: bold;")
        control_layout.addWidget(self.color_btn)
        
        # Brightness control
        bright_label = QLabel("Brightness:")
        bright_label.setStyleSheet("font-weight: bold;")
        control_layout.addWidget(bright_label)
        
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setMinimum(0)
        self.brightness_slider.setMaximum(200)
        self.brightness_slider.setValue(100)
        self.brightness_slider.setTickPosition(QSlider.TicksBelow)
        self.brightness_slider.setTickInterval(25)
        self.brightness_slider.valueChanged.connect(self.change_brightness)
        self.brightness_slider.setMinimumWidth(200)
        control_layout.addWidget(self.brightness_slider)
        
        self.brightness_label = QLabel("100%")
        self.brightness_label.setStyleSheet("font-weight: bold; min-width: 50px;")
        control_layout.addWidget(self.brightness_label)
        
        control_layout.addStretch()
        
        # Clear button
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_all)
        self.clear_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px; font-weight: bold;")
        control_layout.addWidget(self.clear_btn)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # Canvas with border
        canvas_container = QWidget()
        canvas_container.setStyleSheet("border: 3px solid #34495e; border-radius: 5px;")
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        
        self.canvas = Canvas()
        canvas_layout.addWidget(self.canvas)
        main_layout.addWidget(canvas_container)
        
        # Keyframe controls in a group box
        keyframe_group = QGroupBox("Keyframe Controls")
        keyframe_layout = QHBoxLayout()
        
        frame_label = QLabel("Frame:")
        frame_label.setStyleSheet("font-weight: bold;")
        keyframe_layout.addWidget(frame_label)
        
        self.frame_spinbox = QSpinBox()
        self.frame_spinbox.setMinimum(0)
        self.frame_spinbox.setMaximum(self.max_frames - 1)
        self.frame_spinbox.valueChanged.connect(self.goto_frame)
        self.frame_spinbox.setMinimumWidth(80)
        keyframe_layout.addWidget(self.frame_spinbox)
        
        self.add_keyframe_btn = QPushButton("Add Keyframe")
        self.add_keyframe_btn.clicked.connect(self.add_keyframe)
        self.add_keyframe_btn.setStyleSheet("background-color: #f39c12; color: white; padding: 6px; font-weight: bold;")
        keyframe_layout.addWidget(self.add_keyframe_btn)
        
        self.remove_keyframe_btn = QPushButton("Remove Keyframe")
        self.remove_keyframe_btn.clicked.connect(self.remove_keyframe)
        self.remove_keyframe_btn.setStyleSheet("background-color: #c0392b; color: white; padding: 6px; font-weight: bold;")
        keyframe_layout.addWidget(self.remove_keyframe_btn)
        
        # Keyframe info label
        self.keyframe_info_label = QLabel("No object selected")
        self.keyframe_info_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        keyframe_layout.addWidget(self.keyframe_info_label)
        
        keyframe_layout.addStretch()
        
        keyframe_group.setLayout(keyframe_layout)
        main_layout.addWidget(keyframe_group)
        
        # Timeline with label
        timeline_label = QLabel("Timeline (Drag the red bar to scrub)")
        timeline_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        main_layout.addWidget(timeline_label)
        
        self.timeline = Timeline(self.max_frames)
        self.timeline.frame_changed.connect(self.on_timeline_frame_changed)
        main_layout.addWidget(self.timeline)
        
        # Playback controls in a group box
        playback_group = QGroupBox("Playback Controls")
        playback_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.toggle_playback)
        self.play_btn.setStyleSheet("background-color: #16a085; color: white; padding: 10px; font-weight: bold; font-size: 14px;")
        playback_layout.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_playback)
        self.stop_btn.setStyleSheet("background-color: #95a5a6; color: white; padding: 10px; font-weight: bold; font-size: 14px;")
        playback_layout.addWidget(self.stop_btn)
        
        fps_label = QLabel("FPS:")
        fps_label.setStyleSheet("font-weight: bold;")
        playback_layout.addWidget(fps_label)
        
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setMinimum(1)
        self.fps_spinbox.setMaximum(60)
        self.fps_spinbox.setValue(self.fps)
        self.fps_spinbox.valueChanged.connect(self.change_fps)
        self.fps_spinbox.setMinimumWidth(60)
        playback_layout.addWidget(self.fps_spinbox)
        
        playback_layout.addStretch()
        
        # Save/Load
        self.save_btn = QPushButton("Save Animation")
        self.save_btn.clicked.connect(self.save_animation)
        self.save_btn.setStyleSheet("background-color: #8e44ad; color: white; padding: 10px; font-weight: bold;")
        playback_layout.addWidget(self.save_btn)
        
        self.load_btn = QPushButton("Load Animation")
        self.load_btn.clicked.connect(self.load_animation)
        self.load_btn.setStyleSheet("background-color: #2980b9; color: white; padding: 10px; font-weight: bold;")
        playback_layout.addWidget(self.load_btn)
        
        playback_group.setLayout(playback_layout)
        main_layout.addWidget(playback_group)
        
        # Status bar
        self.status_label = QLabel("Ready | Frame: 0 | Objects: 0")
        self.status_label.setStyleSheet("background-color: #ecf0f1; padding: 5px; border-radius: 3px;")
        main_layout.addWidget(self.status_label)
        
        # Update status regularly
        self.update_status()
        
    def add_object(self):
        """Add new object to canvas"""
        obj = self.canvas.add_object()
        self.timeline.update_objects(self.canvas.objects)
        self.update_status()
        
    def change_color(self):
        """Change color of selected object"""
        obj = self.canvas.get_selected_object()
        if obj:
            color = QColorDialog.getColor(obj.base_color, self, "Choose Object Color")
            if color.isValid():
                obj.set_base_color(color)
                self.timeline.draw_keyframes()
        else:
            QMessageBox.warning(self, "No Selection", "Please select an object first")
            
    def change_brightness(self, value):
        """Change brightness of selected object"""
        obj = self.canvas.get_selected_object()
        if obj:
            obj.set_brightness(value)
            self.brightness_label.setText(f"{value}%")
        else:
            self.brightness_label.setText(f"{value}%")
            
    def update_status(self):
        """Update status bar"""
        num_objects = len(self.canvas.objects)
        selected = self.canvas.get_selected_object()
        
        status = f"Frame: {self.current_frame}/{self.max_frames-1} | Objects: {num_objects}"
        
        if selected:
            num_keyframes = len(selected.keyframes)
            has_keyframe_here = self.current_frame in selected.keyframes
            keyframe_marker = " *" if has_keyframe_here else ""
            status += f" | Selected: Obj with {num_keyframes} keyframes{keyframe_marker}"
            self.keyframe_info_label.setText(f"Selected: {num_keyframes} keyframes" + (" * at current frame" if has_keyframe_here else ""))
        else:
            self.keyframe_info_label.setText("No object selected")
            
        if self.is_playing:
            status += " | PLAYING"
            
        self.status_label.setText(status)
            
    def clear_all(self):
        """Clear all objects"""
        reply = QMessageBox.question(self, 'Clear All', 
                                    'Are you sure you want to clear all objects?',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.canvas.clear_all()
            self.timeline.update_objects(self.canvas.objects)
            self.update_status()
            
    def add_keyframe(self):
        """Add keyframe for selected object at current frame"""
        obj = self.canvas.get_selected_object()
        if obj:
            obj.add_keyframe(self.current_frame)
            self.timeline.draw_keyframes()
            self.update_status()
            QMessageBox.information(self, "Keyframe Added", 
                                  f"Keyframe added at frame {self.current_frame}")
        else:
            QMessageBox.warning(self, "No Selection", "Please select an object first")
            
    def remove_keyframe(self):
        """Remove keyframe for selected object at current frame"""
        obj = self.canvas.get_selected_object()
        if obj:
            if self.current_frame in obj.keyframes:
                obj.remove_keyframe(self.current_frame)
                self.timeline.draw_keyframes()
                self.update_status()
                QMessageBox.information(self, "Keyframe Removed", 
                                      f"Keyframe removed from frame {self.current_frame}")
            else:
                QMessageBox.warning(self, "No Keyframe", 
                                  f"No keyframe exists at frame {self.current_frame}")
        else:
            QMessageBox.warning(self, "No Selection", "Please select an object first")
            
    def goto_frame(self, frame):
        """Go to specific frame"""
        self.current_frame = frame
        self.timeline.set_frame(frame)
        self.update_objects_for_frame(frame)
        self.update_status()
        
    def on_timeline_frame_changed(self, frame):
        """Handle frame change from timeline"""
        self.current_frame = frame
        self.frame_spinbox.setValue(frame)
        self.update_objects_for_frame(frame)
        self.update_status()
        
    def update_objects_for_frame(self, frame):
        """Update all objects to their interpolated state at given frame"""
        for obj in self.canvas.objects:
            state = obj.get_interpolated_state(frame)
            if state:
                obj.setPos(state['x'], state['y'])
                obj.set_brightness(state['brightness'])
                
    def toggle_playback(self):
        """Toggle animation playback"""
        if self.is_playing:
            self.timer.stop()
            self.is_playing = False
            self.play_btn.setText("Play")
            self.play_btn.setStyleSheet("background-color: #16a085; color: white; padding: 10px; font-weight: bold; font-size: 14px;")
        else:
            self.timer.start(1000 // self.fps)
            self.is_playing = True
            self.play_btn.setText("Pause")
            self.play_btn.setStyleSheet("background-color: #f39c12; color: white; padding: 10px; font-weight: bold; font-size: 14px;")
        self.update_status()
            
    def stop_playback(self):
        """Stop playback and reset to frame 0"""
        self.timer.stop()
        self.is_playing = False
        self.play_btn.setText("Play")
        self.play_btn.setStyleSheet("background-color: #16a085; color: white; padding: 10px; font-weight: bold; font-size: 14px;")
        self.goto_frame(0)
        
    def next_frame(self):
        """Move to next frame during playback"""
        self.current_frame += 1
        if self.current_frame >= self.max_frames:
            self.current_frame = 0
        self.goto_frame(self.current_frame)
        
    def change_fps(self, fps):
        """Change playback FPS"""
        self.fps = fps
        if self.is_playing:
            self.timer.setInterval(1000 // self.fps)
            
    def save_animation(self):
        """Save animation to JSON file"""
        filename, _ = QFileDialog.getSaveFileName(self, "Save Animation", 
                                                  "", "JSON Files (*.json)")
        if filename:
            data = {
                'max_frames': self.max_frames,
                'fps': self.fps,
                'objects': []
            }
            
            for obj in self.canvas.objects:
                obj_data = {
                    'x': obj.pos().x(),
                    'y': obj.pos().y(),
                    'size': obj.rect().width(),
                    'color': obj.base_color.name(),
                    'brightness': obj.brightness,
                    'keyframes': obj.keyframes
                }
                data['objects'].append(obj_data)
                
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
                
            QMessageBox.information(self, "Success", "Animation saved successfully!")
            
    def load_animation(self):
        """Load animation from JSON file"""
        filename, _ = QFileDialog.getOpenFileName(self, "Load Animation", 
                                                  "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                    
                # Clear current animation
                self.canvas.clear_all()
                
                # Load settings
                self.max_frames = data.get('max_frames', 300)
                self.fps = data.get('fps', 30)
                self.fps_spinbox.setValue(self.fps)
                
                # Load objects
                for obj_data in data.get('objects', []):
                    obj = AnimatedObject(obj_data['x'], obj_data['y'], obj_data['size'])
                    obj.set_base_color(QColor(obj_data['color']))
                    obj.brightness = obj_data.get('brightness', 100)
                    obj.keyframes = {int(k): v for k, v in obj_data.get('keyframes', {}).items()}
                    self.canvas.objects.append(obj)
                    self.canvas.scene.addItem(obj)
                    
                self.timeline.update_objects(self.canvas.objects)
                self.goto_frame(0)
                self.update_status()
                
                QMessageBox.information(self, "Success", "Animation loaded successfully!")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load animation: {str(e)}")


def main():
    app = QApplication(sys.argv)
    window = AnimationSoftware()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
