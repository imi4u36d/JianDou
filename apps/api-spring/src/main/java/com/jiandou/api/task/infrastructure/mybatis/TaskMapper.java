package com.jiandou.api.task.infrastructure.mybatis;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TaskMapper extends BaseMapper<TaskEntity> {
}
