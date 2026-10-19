# 把第 1 周手工创建的资源接管进 Terraform。导入完成并 apply 一次后可以删掉这个文件。

import {
  to = azurerm_resource_group.main
  id = "/subscriptions/${var.subscription_id}/resourceGroups/rg_nz_power"
}

import {
  to = azurerm_storage_account.raw
  id = "/subscriptions/${var.subscription_id}/resourceGroups/rg_nz_power/providers/Microsoft.Storage/storageAccounts/nzpowerhxu"
}

import {
  to = azurerm_storage_container.raw
  id = "/subscriptions/${var.subscription_id}/resourceGroups/rg_nz_power/providers/Microsoft.Storage/storageAccounts/nzpowerhxu/blobServices/default/containers/raw"
}
