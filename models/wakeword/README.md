# 唤醒词模型目录

这个目录用于存放OpenWakeWord的唤醒词模型文件（.tflite或.onnx格式）。

## 自动下载模型（推荐）

**方法1：程序会在首次运行时自动下载**

首次启用唤醒词模块时，程序会自动下载所有预训练模型到这个目录。

**方法2：手动在Python中下载**

```python
import openwakeword

# 下载所有预训练模型
openwakeword.utils.download_models()
```

**方法3：在终端命令行下载**

```bash
python -c "import openwakeword; openwakeword.utils.download_models('/Users/wangjie/project/other/kiwi/models/wakeword')"
```

## 预训练模型列表

OpenWakeWord提供以下预训练唤醒词模型：

1. **alexa** - "Alexa"
2. **hey_jarvis** - "Hey Jarvis"
3. **hey_mycroft** - "Hey Mycroft"  
4. **hey_rhasspy** - "Hey Rhasspy"
5. **timer** - "Set a timer"
6. **weather** - "What's the weather"

## 手动下载（备选方案）

如果自动下载失败，可以从GitHub Releases手动下载：

**下载地址：**
https://github.com/dscripka/openWakeWord/releases

1. 进入最新的Release页面
2. 在Assets中找到模型文件（.tflite或.onnx格式）
3. 下载后放到这个目录

## 使用方法

1. 确保模型文件已下载到本目录
2. 在配置文件中启用唤醒词模块：
   ```yaml
   modules:
     wakeword:
       enabled: true
   ```
3. 重启应用，系统会自动加载所有模型

## 自定义唤醒词

如果你想创建自己的唤醒词（如"Hey Kiwi"），可以：

1. 访问 https://github.com/dscripka/openWakeWord
2. 使用Google Colab训练工具: https://colab.research.google.com/drive/1q1oe2zOyZp7UsB3jJiQ1IFn8z5YfjwEb
3. 将训练好的模型文件放到这个目录

## 注意事项

- 支持.tflite和.onnx两种格式的模型文件
- 文件名会作为唤醒词的标识
- 可以同时放置多个模型，系统会自动加载所有模型
- 首次下载可能需要几分钟时间
