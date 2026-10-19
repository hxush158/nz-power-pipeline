# 这些资源在第 1 周手工创建，这里用 import 接管（见 imports.tf），不会重建。
# 两处 prevent_destroy：误执行 destroy 或属性变化需要重建时，Terraform 会直接报错而不是删掉数据。

resource "azurerm_resource_group" "main" {
  name     = "rg_nz_power"
  location = var.location

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_storage_account" "raw" {
  name                     = "nzpowerhxu"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  # ADLS Gen2 需要开启分层命名空间；这个值与现有资源不一致会触发重建，所以 plan 时要特别看。
  is_hns_enabled = true
  # 现有账号不允许把数据设为公开访问；Terraform 默认值是 true，必须显式写成 false，
  # 否则 apply 会把这个安全设置改掉。
  allow_nested_items_to_be_public = false

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_storage_container" "raw" {
  name                  = "raw"
  storage_account_id    = azurerm_storage_account.raw.id
  container_access_type = "private"
}

# Terraform 状态文件的存放容器（私有）。状态里包含存储账号的访问密钥，不能公开，也不能提交到仓库。
resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.raw.id
  container_access_type = "private"

  lifecycle {
    prevent_destroy = true
  }
}

# 订阅级月度预算：实际花费达到 50% 和 90%、预测花费达到 100% 时发邮件。
data "azurerm_subscription" "current" {}

resource "azurerm_consumption_budget_subscription" "monthly" {
  name            = "monthly-budget"
  subscription_id = data.azurerm_subscription.current.id
  amount          = var.budget_amount
  time_grain      = "Monthly"

  time_period {
    start_date = "2026-10-01T00:00:00Z"
  }

  notification {
    enabled        = true
    threshold      = 50
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = [var.alert_email]
  }

  notification {
    enabled        = true
    threshold      = 90
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = [var.alert_email]
  }

  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThan"
    threshold_type = "Forecasted"
    contact_emails = [var.alert_email]
  }
}
