#!/usr/bin/env python
"""
交互式车辆控制台
实时执行工具并查看状态变化
"""
import asyncio
from . import get_tool_registry, get_vehicle_state


class VehicleConsole:
    """车辆控制台"""
    
    def __init__(self):
        self.registry = get_tool_registry()
        self.vehicle = get_vehicle_state()
        self.running = True
    
    def print_header(self):
        """打印标题"""
        print("\n" + "=" * 70)
        print("🚗  KIWI 车辆控制台  🚗".center(70))
        print("=" * 70)
        print(f"工具总数: {len(self.registry.tools)} | 分类: 15")
        print("=" * 70)
    
    def print_menu(self):
        """打印菜单"""
        print("\n【主菜单】")
        print("  1. 列出所有工具")
        print("  2. 按分类查看工具")
        print("  3. 执行工具")
        print("  4. 查看车辆状态")
        print("  5. 快捷场景")
        print("  0. 退出")
        print()
    
    def list_all_tools(self):
        """列出所有工具"""
        print("\n" + "=" * 70)
        print("所有工具列表")
        print("=" * 70)
        
        by_category = {}
        for tool in self.registry.tools.values():
            cat = tool.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(tool.name)
        
        for cat in sorted(by_category.keys()):
            print(f"\n【{cat}】 ({len(by_category[cat])}个工具)")
            for name in sorted(by_category[cat]):
                tool = self.registry.get_tool(name)
                print(f"  • {name:<30} - {tool.description}")
    
    def list_by_category(self):
        """按分类查看工具"""
        print("\n【工具分类】")
        categories = {
            "1": ("vehicle_control", "车辆控制"),
            "2": ("climate", "空调系统"),
            "3": ("entertainment", "娱乐系统"),
            "4": ("navigation", "导航系统"),
            "5": ("window", "车窗/天窗"),
            "6": ("seat", "座椅调节"),
            "7": ("lighting", "灯光控制"),
            "8": ("safety", "安全系统"),
            "9": ("adas", "驾驶辅助"),
            "10": ("door", "车门/后备箱"),
            "11": ("wiper", "雨刷系统"),
            "12": ("ambient", "氛围系统"),
            "13": ("information", "信息查询"),
        }
        
        for key, (cat_id, cat_name) in categories.items():
            print(f"  {key}. {cat_name}")
        
        choice = input("\n请选择分类 (1-13): ").strip()
        if choice in categories:
            cat_id, cat_name = categories[choice]
            tools = [t for t in self.registry.tools.values() if t.category.value == cat_id]
            
            print(f"\n【{cat_name}】 共{len(tools)}个工具")
            print("-" * 70)
            for tool in sorted(tools, key=lambda t: t.name):
                print(f"  • {tool.name:<30} - {tool.description}")
                if tool.parameters:
                    print(f"    参数: {', '.join(p.name for p in tool.parameters)}")
    
    async def execute_tool(self):
        """执行工具"""
        tool_name = input("\n请输入工具名称: ").strip()
        
        tool = self.registry.get_tool(tool_name)
        if not tool:
            print(f"❌ 工具 '{tool_name}' 不存在")
            return
        
        print(f"\n工具: {tool.name}")
        print(f"描述: {tool.description}")
        
        # 收集参数
        kwargs = {}
        if tool.parameters:
            print(f"\n需要的参数:")
            for param in tool.parameters:
                print(f"  • {param.name} ({param.type}): {param.description}")
                if param.enum:
                    print(f"    可选值: {', '.join(param.enum)}")
                if hasattr(param, 'default') and param.default is not None:
                    print(f"    默认值: {param.default}")
            
            print()
            for param in tool.parameters:
                value = input(f"  {param.name}: ").strip()
                if value:
                    # 类型转换
                    if param.type == "number":
                        try:
                            kwargs[param.name] = float(value) if '.' in value else int(value)
                        except ValueError:
                            print(f"  ⚠️  参数 {param.name} 应为数字")
                    elif param.type == "boolean":
                        kwargs[param.name] = value.lower() in ('true', 'yes', '1', 'y')
                    else:
                        kwargs[param.name] = value
        
        # 执行工具
        print(f"\n正在执行...")
        try:
            result = await tool.execute(**kwargs)
            print(f"\n✅ 执行成功")
            print(f"结果: {result}")
        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
    
    def show_status(self):
        """显示车辆状态"""
        print("\n" + "=" * 70)
        print("车辆状态")
        print("=" * 70)
        
        state = self.vehicle.state
        
        print("\n【基本信息】")
        print(f"  发动机: {'✅ 运行中' if self.vehicle.is_engine_running() else '❌ 熄火'}")
        print(f"  车门: {'🔒 已锁定' if state.doors_locked else '🔓 已解锁'}")
        print(f"  车速: {self.vehicle.get_speed()} km/h")
        print(f"  油量: {self.vehicle.get_fuel_level()}%")
        print(f"  电量: {self.vehicle.get_battery_level()}%")
        print(f"  驾驶模式: {state.driving_mode}")
        
        print("\n【空调系统】")
        print(f"  空调: {'✅ 开启' if state.ac_on else '❌ 关闭'}")
        print(f"  驾驶侧温度: {self.vehicle.get_temperature('driver')}℃")
        print(f"  乘客侧温度: {self.vehicle.get_temperature('passenger')}℃")
        print(f"  风速: {state.fan_speed}级")
        print(f"  自动模式: {'✅' if state.auto_climate else '❌'}")
        
        print("\n【娱乐系统】")
        print(f"  音乐: {'▶️  播放中' if state.music_playing else '⏸️  暂停'}")
        print(f"  音量: {self.vehicle.get_volume()}")
        print(f"  静音: {'🔇 是' if state.muted else '🔊 否'}")
        print(f"  蓝牙: {'✅ 已连接' if state.bluetooth_enabled else '❌ 未连接'}")
        
        print("\n【导航系统】")
        print(f"  导航: {'✅ 活跃' if state.navigation_active else '❌ 未激活'}")
        if state.navigation_active:
            print(f"  目的地: {state.navigation_destination}")
        print(f"  语音导航: {'✅' if state.voice_guidance else '❌'}")
        
        print("\n【车窗状态】")
        print(f"  驾驶侧: {state.windows['driver']}%")
        print(f"  乘客侧: {state.windows['passenger']}%")
        print(f"  天窗: {state.sunroof_position}%")
        
        print("\n【灯光】")
        print(f"  大灯: {'✅' if state.headlights_on else '❌'} ({state.headlight_mode})")
        print(f"  氛围灯: {'✅' if state.ambient_lights_on else '❌'} ({state.ambient_light_color})")
        
        print("\n【安全辅助】")
        print(f"  车道保持: {'✅' if state.lane_assist else '❌'}")
        print(f"  盲区监测: {'✅' if state.blind_spot_monitor else '❌'}")
        print(f"  碰撞预警: {'✅' if state.collision_warning else '❌'}")
        print(f"  定速巡航: {'✅ ' + str(state.cruise_control_speed) + ' km/h' if state.cruise_control_enabled else '❌'}")
    
    async def quick_scenarios(self):
        """快捷场景"""
        print("\n【快捷场景】")
        print("  1. 启动车辆（解锁+启动）")
        print("  2. 开启舒适模式（空调+音乐）")
        print("  3. 导航回家")
        print("  4. 开启驾驶辅助")
        print("  5. 停车锁车")
        
        choice = input("\n请选择场景 (1-5): ").strip()
        
        scenarios = {
            "1": self.scenario_start,
            "2": self.scenario_comfort,
            "3": self.scenario_go_home,
            "4": self.scenario_adas,
            "5": self.scenario_park,
        }
        
        if choice in scenarios:
            await scenarios[choice]()
    
    async def scenario_start(self):
        """场景1: 启动车辆"""
        print("\n🚗 启动车辆...")
        await self.registry.get_tool("unlock_vehicle").execute()
        print("  ✓ 解锁车辆")
        await self.registry.get_tool("start_engine").execute()
        print("  ✓ 启动发动机")
        print("✅ 车辆已启动")
    
    async def scenario_comfort(self):
        """场景2: 舒适模式"""
        print("\n😊 开启舒适模式...")
        await self.registry.get_tool("turn_on_ac").execute()
        print("  ✓ 空调已开启")
        await self.registry.get_tool("set_temperature").execute(zone="all", temperature=24)
        print("  ✓ 温度设置为24℃")
        await self.registry.get_tool("play_music").execute()
        print("  ✓ 音乐播放中")
        await self.registry.get_tool("set_volume").execute(volume=50)
        print("  ✓ 音量50")
        print("✅ 舒适模式已开启")
    
    async def scenario_go_home(self):
        """场景3: 导航回家"""
        print("\n🏠 导航回家...")
        await self.registry.get_tool("navigate_home").execute()
        print("  ✓ 导航已启动")
        await self.registry.get_tool("enable_voice_guidance").execute()
        print("  ✓ 语音导航已开启")
        print("✅ 正在导航回家")
    
    async def scenario_adas(self):
        """场景4: 驾驶辅助"""
        print("\n🛡️  开启驾驶辅助...")
        await self.registry.get_tool("enable_lane_assist").execute()
        print("  ✓ 车道保持")
        await self.registry.get_tool("enable_blind_spot_monitor").execute()
        print("  ✓ 盲区监测")
        await self.registry.get_tool("enable_collision_warning").execute()
        print("  ✓ 碰撞预警")
        print("✅ 驾驶辅助已开启")
    
    async def scenario_park(self):
        """场景5: 停车锁车"""
        print("\n🅿️  停车...")
        await self.registry.get_tool("stop_engine").execute()
        print("  ✓ 发动机已熄火")
        await self.registry.get_tool("lock_vehicle").execute()
        print("  ✓ 车辆已锁定")
        print("✅ 停车完成")
    
    async def run(self):
        """运行控制台"""
        self.print_header()
        
        while self.running:
            self.print_menu()
            choice = input("请选择操作 (0-5): ").strip()
            
            if choice == "0":
                print("\n👋 再见！")
                self.running = False
            elif choice == "1":
                self.list_all_tools()
            elif choice == "2":
                self.list_by_category()
            elif choice == "3":
                await self.execute_tool()
            elif choice == "4":
                self.show_status()
            elif choice == "5":
                await self.quick_scenarios()
            else:
                print("❌ 无效选择")
            
            if self.running:
                input("\n按回车继续...")


async def main():
    """主函数"""
    console = VehicleConsole()
    await console.run()


if __name__ == "__main__":
    asyncio.run(main())
