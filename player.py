import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import pygame
import os
import time
import traceback
import subprocess
import tempfile
import json
from datetime import datetime

class AudioPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("高兼容音频播放器 v2.3")
        self.root.geometry("600x400")
        
        # 初始化变量
        self.playing = False
        self.paused = False
        self.current_file = None
        self.temp_file = None
        self.duration = 0
        self.volume_level = 0.75
        self.start_time = 0
        self.audio_ready = False
        
        # 播放历史
        self.history_file = "play_history.json"
        self.play_history = []
        
        # 初始化音频系统
        self._init_audio()
        self._load_history()
        self._create_ui()
        
        root.protocol("WM_DELETE_WINDOW", self._safe_exit)

    def _init_audio(self):
        """初始化音频系统"""
        try:
            pygame.mixer.quit()
            # 尝试常见配置
            try:
                pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
                pygame.mixer.init()
                if pygame.mixer.get_init() is not None:
                    self.audio_ready = True
                    pygame.mixer.music.set_volume(self.volume_level)
                    print("音频系统初始化成功")
                    return
            except:
                pass
            
            # 如果失败，尝试默认初始化
            pygame.mixer.init()
            self.audio_ready = pygame.mixer.get_init() is not None
            if self.audio_ready:
                pygame.mixer.music.set_volume(self.volume_level)
            else:
                raise RuntimeError("无法初始化音频系统")
                
        except Exception as e:
            print(f"音频初始化失败: {str(e)}")
            self.audio_ready = False

    def _create_ui(self):
        """创建用户界面"""
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧控制面板
        control_frame = tk.Frame(main_frame)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 文件信息
        self.file_label = tk.Label(
            control_frame, 
            text="未加载文件",
            font=("Arial", 10),
            anchor=tk.W,
            width=30
        )
        self.file_label.pack(fill=tk.X, pady=5)
        
        # 控制按钮
        btn_frame = tk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.btn_open = tk.Button(
            btn_frame,
            text="选择音频",
            command=self._open_file,
            width=10
        )
        self.btn_open.pack(side=tk.LEFT)
        
        self.btn_play = tk.Button(
            btn_frame,
            text="播放",
            command=self._toggle_play,
            width=8,
            state=tk.DISABLED
        )
        self.btn_play.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = tk.Button(
            btn_frame,
            text="停止",
            command=self._stop,
            width=8,
            state=tk.DISABLED
        )
        self.btn_stop.pack(side=tk.LEFT)
        
        # 音量控制
        volume_frame = tk.Frame(control_frame)
        volume_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(volume_frame, text="音量:").pack(side=tk.LEFT)
        self.volume_scale = ttk.Scale(
            volume_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=lambda v: self._set_volume(float(v)/100)
        )
        self.volume_scale.set(self.volume_level * 100)
        self.volume_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 进度条
        self.progress = ttk.Scale(
            control_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=self._on_seek
        )
        self.progress.pack(fill=tk.X, pady=10)
        
        # 时间显示
        self.time_label = tk.Label(
            control_frame,
            text="00:00 / 00:00",
            font=("Consolas", 12)
        )
        self.time_label.pack()
        
        # 状态栏
        self.status_label = tk.Label(
            control_frame,
            text="就绪" if self.audio_ready else "音频系统未就绪",
            fg="green" if self.audio_ready else "red"
        )
        self.status_label.pack(fill=tk.X, pady=5)
        
        # 右侧历史记录面板
        history_frame = tk.Frame(main_frame, borderwidth=1, relief="sunken")
        history_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        tk.Label(history_frame, text="播放历史", font=("Arial", 10, "bold")).pack(pady=5)
        
        # 历史记录列表
        self.history_listbox = tk.Listbox(
            history_frame,
            height=15,
            selectmode=tk.SINGLE
        )
        self.history_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.history_listbox.bind("<Double-Button-1>", self._play_from_history)
        
        # 历史记录控制按钮
        history_btn_frame = tk.Frame(history_frame)
        history_btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(
            history_btn_frame,
            text="清除历史",
            command=self._clear_history,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            history_btn_frame,
            text="刷新",
            command=self._refresh_history,
            width=10
        ).pack(side=tk.LEFT)
        
        self._refresh_history()

    def _set_volume(self, volume):
        """设置音量"""
        self.volume_level = volume
        if self.audio_ready:
            pygame.mixer.music.set_volume(volume)

    def _load_history(self):
        """加载播放历史"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.play_history = json.load(f)
        except:
            self.play_history = []

    def _save_history(self):
        """保存播放历史"""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.play_history, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _add_to_history(self, file_path):
        """添加记录到播放历史"""
        if not file_path:
            return
            
        # 检查是否已存在相同记录
        for item in self.play_history:
            if item["path"] == file_path:
                item["last_played"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._save_history()
                self._refresh_history()
                return
                
        # 添加新记录
        self.play_history.append({
            "path": file_path,
            "name": os.path.basename(file_path),
            "last_played": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 限制历史记录数量
        if len(self.play_history) > 50:
            self.play_history = self.play_history[-50:]
            
        self._save_history()
        self._refresh_history()

    def _refresh_history(self):
        """刷新历史记录显示"""
        self.history_listbox.delete(0, tk.END)
        for item in sorted(self.play_history, key=lambda x: x["last_played"], reverse=True):
            display_text = f"{item['name']} ({item['last_played']})"
            self.history_listbox.insert(tk.END, display_text)

    def _clear_history(self):
        """清除播放历史"""
        if messagebox.askyesno("确认", "确定要清除所有播放历史记录吗？"):
            self.play_history = []
            self._save_history()
            self._refresh_history()

    def _play_from_history(self, event):
        """从历史记录中选择并播放"""
        selection = self.history_listbox.curselection()
        if selection:
            index = selection[0]
            if 0 <= index < len(self.play_history):
                file_path = self.play_history[index]["path"]
                if os.path.exists(file_path):
                    self._load_audio(file_path)
                else:
                    messagebox.showerror("错误", "文件不存在或已被移动")

    def _open_file(self):
        """打开音频文件"""
        filetypes = [
            ("音频文件", "*.mp3 *.wav *.ogg *.flac *.aac *.m4a"),
            ("所有文件", "*.*")
        ]
        
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self._load_audio(path)
            self._add_to_history(path)

    def _load_audio(self, path):
        """加载音频文件"""
        self._stop()
        self._update_status("加载中...", "blue")
        
        try:
            # 先尝试直接加载
            try:
                pygame.mixer.music.load(path)
                self.current_file = path
                self._prepare_audio(path)
            except pygame.error as e:
                # 如果直接加载失败，尝试修复文件
                if "corrupt" in str(e).lower() or "invalid" in str(e).lower():
                    self._repair_audio_file(path)
                else:
                    raise
                    
            self.file_label.config(text=os.path.basename(path))
            self._enable_controls()
            self._update_status("加载成功", "green")
            
        except Exception as e:
            self._show_error("加载失败", f"无法加载音频: {str(e)}")
            self._update_status("加载失败", "red")
            print(traceback.format_exc())

    def _repair_audio_file(self, path):
        """尝试修复损坏的音频文件"""
        try:
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_file.close()
            
            # 使用FFmpeg转换格式
            if self._has_ffmpeg():
                self._convert_with_ffmpeg(path, temp_file.name)
            else:
                # 如果没有FFmpeg，尝试用Sound对象转换
                self._convert_with_pygame(path, temp_file.name)
            
            # 加载转换后的文件
            pygame.mixer.music.load(temp_file.name)
            self.current_file = path  # 记住原始路径
            self.temp_file = temp_file  # 保留临时文件引用
            self._prepare_audio(temp_file.name)
            
        except Exception as e:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise RuntimeError(f"文件修复失败: {str(e)}")

    def _has_ffmpeg(self):
        """检查系统是否安装FFmpeg"""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True
        except:
            return False

    def _convert_with_ffmpeg(self, input_path, output_path):
        """使用FFmpeg转换音频格式"""
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            "-af", "dynaudnorm",
            "-loglevel", "error",
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg转换失败: {result.stderr.decode()}")

    def _convert_with_pygame(self, input_path, output_path):
        """使用Pygame Sound对象转换格式"""
        try:
            sound = pygame.mixer.Sound(input_path)
            self._show_error("格式问题", "建议安装FFmpeg以获得更好兼容性")
            raise RuntimeError("无FFmpeg时无法自动修复MP3文件")
        except Exception as e:
            raise RuntimeError(f"Pygame无法读取文件: {str(e)}")

    def _prepare_audio(self, path):
        """准备播放音频"""
        try:
            sound = pygame.mixer.Sound(path)
            self.duration = sound.get_length()
            self.playing = True
            self._play()
        except:
            self.duration = 0
            self.playing = True
            self._play()

    def _play(self):
        """开始播放"""
        if not self.audio_ready or not self.current_file:
            return
            
        try:
            pygame.mixer.music.play()
            self.start_time = time.time()
            self._update_progress()
            self.btn_play.config(text="暂停")
            self._update_status("播放中...", "blue")
        except Exception as e:
            self._show_error("播放失败", str(e))

    def _toggle_play(self):
        """切换播放/暂停"""
        if not self.current_file:
            return
            
        if self.playing:
            if self.paused:
                self._resume()
            else:
                self._pause()
        else:
            self._play()

    def _pause(self):
        """暂停播放"""
        pygame.mixer.music.pause()
        self.paused = True
        self.btn_play.config(text="播放")
        self._update_status("已暂停", "blue")

    def _resume(self):
        """恢复播放"""
        pygame.mixer.music.unpause()
        self.paused = False
        self.btn_play.config(text="暂停")
        self._update_status("播放中...", "blue")
        self._update_progress()

    def _stop(self):
        """停止播放"""
        pygame.mixer.music.stop()
        if self.temp_file:
            try:
                os.unlink(self.temp_file.name)
            except:
                pass
            self.temp_file = None
            
        self.playing = False
        self.paused = False
        self._disable_controls()
        self.time_label.config(text="00:00 / 00:00")
        self.progress.set(0)
        self._update_status("已停止", "green")

    def _on_seek(self, value):
        """处理进度跳转"""
        if not self.playing or not self.current_file:
            return
            
        try:
            percent = float(value) / 100
            seek_time = percent * self.duration
            
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.set_pos(seek_time)
                self.start_time = time.time() - seek_time
            
            self._update_time(seek_time)
        except:
            pass

    def _update_progress(self):
        """更新播放进度"""
        if not self.playing or self.paused:
            return
            
        try:
            if pygame.mixer.music.get_busy():
                elapsed = time.time() - self.start_time
                if self.duration > 0:
                    self.progress.set((elapsed / self.duration) * 100)
                self._update_time(elapsed)
                
                self.root.after(100, self._update_progress)
            else:
                self._stop()
        except:
            pass

    def _update_time(self, current):
        """更新时间显示"""
        current_str = time.strftime('%M:%S', time.gmtime(current))
        total_str = time.strftime('%M:%S', time.gmtime(self.duration)) if self.duration > 0 else "00:00"
        self.time_label.config(text=f"{current_str} / {total_str}")

    def _update_status(self, text, color):
        """更新状态栏"""
        self.status_label.config(text=text, fg=color)

    def _enable_controls(self):
        """启用控制按钮"""
        self.btn_play.config(state=tk.NORMAL, text="播放")
        self.btn_stop.config(state=tk.NORMAL)

    def _disable_controls(self):
        """禁用控制按钮"""
        self.btn_play.config(state=tk.DISABLED, text="播放")
        self.btn_stop.config(state=tk.DISABLED)

    def _show_error(self, title, message):
        """显示错误信息"""
        messagebox.showerror(title, message)

    def _safe_exit(self):
        """安全退出"""
        self._stop()
        self._save_history()
        self.root.destroy()

if __name__ == "__main__":
    try:
        pygame.init()
        root = tk.Tk()
        app = AudioPlayer(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("错误", f"程序崩溃: {str(e)}")
    finally:
        pygame.quit()