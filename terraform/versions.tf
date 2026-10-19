terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

# 认证用 `az login` 的当前登录；订阅 ID 通过环境变量 TF_VAR_subscription_id 传入。
provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}
