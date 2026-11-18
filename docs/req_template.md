# 需求规格说明书

## 实体

### 实体列表

实体名称|说明
-|-
商品|在电商系统中主要实体，客户可在线浏览并下单购买
...|...

### ER图

```plantuml
@startuml 商品管理ER图

title 商品管理系统ER图

entity "商家" as merchant
entity "商品" as product
entity "商品分类" as category
entity "审核记录" as audit
entity "广告" as advertisement
entity "用户" as user
entity "发送记录" as send_log

' 关系
merchant ||--o{ product : "拥有"
product }o--|| category : "属于"
product ||--o| audit : "审核"
merchant ||--o{ advertisement : "创建"
advertisement ||--o{ send_log : "产生"
send_log }o--o{ user : "发送给"

@enduml

```

## 用例

### 商品管理

#### 用例列表

用例|功能说明
-|-
商品列表|显示本店铺所有商品，支持条件过滤
商品详情|点击查看商品明细
...|...

#### 用例图

```plantuml
@startuml 商品管理用例图

title 商品管理用例图

left to right direction

actor 商家 as merchant
actor 审核员 as auditor

rectangle 商品管理系统 {
  
  package "商品管理" {
    usecase "商品列表" as UC1
    usecase "商品详情" as UC2
    usecase "添加商品" as UC3
    usecase "编辑商品" as UC4
    usecase "删除商品" as UC5
  }
  
  package "商品审核" {
    usecase "提交审核" as UC6
    usecase "审核商品" as UC7
  }
  
  package "商品上下架" {
    usecase "上架商品" as UC8
    usecase "下架商品" as UC9
  }
  
  package "库存管理" {
    usecase "更新库存" as UC10
  }
}

' 商家用例
merchant --> UC1 : 查看商品列表
merchant --> UC2 : 查看商品详情
merchant --> UC3 : 添加新商品
merchant --> UC4 : 编辑商品信息
merchant --> UC5 : 删除商品
merchant --> UC6 : 提交审核
merchant --> UC8 : 上架商品
merchant --> UC9 : 下架商品
merchant --> UC10 : 更新库存

' 审核员用例
auditor --> UC7 : 审核商品
auditor --> UC1 : 查看商品列表
auditor --> UC2 : 查看商品详情

' 用例关系
UC1 ..> UC2 : <<include>>
UC3 ..> UC6 : <<include>>
UC4 ..> UC6 : <<include>>
UC8 ..> UC7 : <<include>>

note right of UC1
  显示本店铺所有商品
  支持条件过滤
end note

note right of UC2
  点击查看商品明细
  包括基本信息、价格、库存等
end note

note right of UC7
  审核员审核商品信息
  审核通过后可上架
end note

@enduml

```

### 推广

#### 用例列表

用例|功能说明
-|-
自动发广告|每个月发送配置的广告给配置的用户
...|...

#### 用例图

```plantuml
@startuml 推广管理用例图

title 推广管理用例图

left to right direction

actor 商家 as merchant
actor 系统 as system

rectangle 推广管理系统 {
  
  package "广告管理" {
    usecase "创建广告" as UC1
    usecase "广告列表" as UC2
    usecase "编辑广告" as UC3
    usecase "删除广告" as UC4
  }
  
  package "广告配置" {
    usecase "配置发送时间" as UC5
    usecase "配置目标用户" as UC6
  }
  
  package "自动推广" {
    usecase "自动发广告" as UC7
    usecase "发送记录" as UC8
  }
  
  package "效果统计" {
    usecase "效果统计" as UC9
  }
}

' 商家用例
merchant --> UC1 : 创建新广告
merchant --> UC2 : 查看广告列表
merchant --> UC3 : 编辑广告信息
merchant --> UC4 : 删除广告
merchant --> UC5 : 配置发送时间
merchant --> UC6 : 配置目标用户
merchant --> UC8 : 查看发送记录
merchant --> UC9 : 查看效果统计

' 系统用例
system --> UC7 : 自动发送广告

' 用例关系
UC1 ..> UC5 : <<include>>
UC1 ..> UC6 : <<include>>
UC2 ..> UC1 : <<extend>>
UC7 ..> UC5 : <<include>>
UC7 ..> UC6 : <<include>>
UC7 ..> UC8 : <<include>>

note right of UC7
  每个月发送配置的广告
  给配置的用户
end note

note right of UC5
  配置广告发送的时间
  如每月1号、每周一等
end note

note right of UC6
  配置接收广告的用户
  可按分组、标签筛选
end note

@enduml

```

## 流程说明

### 商品上架流程

#### 流程说明

商品经过上架流程后，可以对外进行展示和销售，包括审核以及下架等...

#### 流程图

```plantuml
@startuml 商品流程状态图

title 商品流程状态图

[*] --> 草稿 : 创建商品

state 草稿 {
  草稿 : 商品信息录入
  草稿 : 可编辑商品信息
}

草稿 --> 待审核 : 提交审核
待审核 --> 草稿 : 审核不通过\n退回修改

待审核 --> 已上架 : 审核通过

state 已上架 {
  已上架 : 商品可被搜索
  已上架 : 商品可被浏览
}

已上架 --> 销售中 : 有订单产生

state 销售中 {
  销售中 : 处理订单
  销售中 : 更新库存
}

销售中 --> 已上架 : 订单完成\n继续销售
销售中 --> 库存不足 : 库存为0

库存不足 --> 已上架 : 补货完成
库存不足 --> 已下架 : 停止补货

已上架 --> 已下架 : 主动下架

state 已下架 {
  已下架 : 商品不可见
  已下架 : 保留商品信息
}

已下架 --> 已上架 : 重新上架
已下架 --> 已删除 : 删除商品

已删除 --> [*] : 商品移除

note right of 草稿
  商品初始状态
  可以随时编辑
end note

note right of 待审核
  等待管理员审核
  审核通过后才能上架
end note

note right of 已上架
  商品正常销售状态
  用户可以看到和购买
end note

note right of 销售中
  有订单正在处理
  需要更新库存信息
end note

note right of 库存不足
  库存为0
  需要补货或下架
end note

note right of 已下架
  商品暂时不可见
  可以重新上架
end note

@enduml

```