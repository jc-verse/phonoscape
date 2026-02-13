function data = mdp_traj(data, varargin)
%MDP_TRAJ  - MVIEW dataproc that appends separately scaled trajectories
%
%	varargin{1} - cellstr list of trajectories, followed by optional common scaling factor and
%	                low-pass Fc (default none)
%
% Because this takes arguments (the cellstr array of trajectories) it must be embedded as
% a cell element within the DPROC list (i.e., nested within {})
%
% usage example:  mview(...,'DPROC',{{'mdp_traj',{'TT','TD'}}}, ...)
% clip to 10 mm: mview(...,'DPROC',{{'mdp_traj',{'HEAD1','HEAD2',10}}}, ...)
% clip to 10 mm after LP filtering @5Hz: mview(...,'DPROC',{{'mdp_traj',{'HEAD1','HEAD2',[10 5]}}}, ...)

% mkt 11/13

names = upper({data.NAME});
traj = varargin(1:end-1);		% last arg is {pal,phar,labs}
filt = [];
if ischar(traj{end}),
	scale = [];
else,
	scale = traj{end};
	if length(scale) > 1,
		filt = scale(2);
		scale = scale(1);
	end;
	traj(end) = [];
end;
XYZ = 'XYZ';
for ti = 1 : length(traj),
	k = strmatch(traj{ti},names,'exact');
	if isempty(k),
		error('%s not found in dataset', traj{ti});
	end;

	n = min([3 size(data(k).SIGNAL,2)]);
	if n > 1, ds = data(k).SIGNAL(:,1:3); else, ds = data(k).SIGNAL; end
	if ~isempty(filt),
		sr = data(k).SRATE;
		[b,a] = butter(3,filt*2/sr,'low');
		fq = NaN(size(ds));
		bad = find(isnan(ds));
		good = find(all(~isnan(ds),2));
		if isempty(good), 					% all bad -- give up
			error('missing data in all %d frames of %s', size(ds,1), traj{ti});
		end;
		if isempty(bad),
			qq = ds;						% none are missing
		else,								% interpolate across missing data points for LP filtering
			qq = interp1(good,ds(good,:),linspace(good(1),good(end),good(end)-good(1)+1)','pchip');
			fprintf('missing data in %d / %d frames of %s', sum(any(isnan(ds),2)), size(ds,1), traj{ti});
		end;
		fq(good(1):good(end),:) = filtfilt(b,a,qq);
		fq(bad) = NaN;						% restore missing status
		ds = fq;
	end;
	
	for xi = 1 : n,
		data(end+1) = data(k);
		data(end).NAME = sprintf('%sF%s',traj{ti},XYZ(xi));
		data(end).SIGNAL = ds(:,xi);
		data(end).NCOMPS = 1;
		if ~isempty(scale),
			data(end).SIGNAL(data(end).SIGNAL > scale) = NaN;
		end;
	end
end;
